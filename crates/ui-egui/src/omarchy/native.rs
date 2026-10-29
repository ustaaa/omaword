use super::{FontFace, Snapshot, files};
use std::io::Read;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex, mpsc};
use std::time::{Duration, Instant};

const POLL: Duration = Duration::from_secs(1);
const FONT_LIMIT: usize = 32 * 1024 * 1024;

pub(super) struct Worker {
    latest: Arc<Mutex<Snapshot>>,
    stop: mpsc::SyncSender<()>,
}

impl Worker {
    pub fn start(ctx: egui::Context) -> Option<Self> {
        let roots = files::roots(
            std::env::var_os("XDG_STATE_HOME").map(PathBuf::from),
            std::env::var_os("XDG_CONFIG_HOME").map(PathBuf::from),
            std::env::var_os("HOME").map(PathBuf::from),
        );
        let latest = Arc::new(Mutex::new(Snapshot::default()));
        let shared = latest.clone();
        let (stop, stopped) = mpsc::sync_channel(1);
        std::thread::Builder::new()
            .name("omaword-appearance".into())
            .spawn(move || {
                let mut selected = None;
                let mut last = Snapshot::default();
                let mut font_poll = 0_u8;
                loop {
                    let mut next = last.clone();
                    if let Some(palette) = files::read_palette(&roots, &mut selected) {
                        next.palette = Some(palette);
                    }
                    if next.palette.is_some() && (font_poll == 0 || next.palette != last.palette) {
                        // Resolve the user's fontconfig monospace aliases, including their chosen Nerd Font.
                        if let Some(normal) = font_face("monospace") {
                            let bold = font_face("monospace:weight=bold").unwrap_or_else(|| normal.clone());
                            next.fonts = Some((normal, bold));
                        }
                    }
                    font_poll = (font_poll + 1) % 10;
                    if next != last {
                        if let Ok(mut value) = shared.lock() {
                            *value = next.clone();
                        }
                        last = next;
                        ctx.request_repaint();
                    }
                    if !matches!(stopped.recv_timeout(POLL), Err(mpsc::RecvTimeoutError::Timeout)) {
                        break;
                    }
                }
            })
            .ok()?;
        Some(Self { latest, stop })
    }

    pub fn current(&self) -> Option<Snapshot> {
        self.latest.try_lock().ok().map(|value| value.clone())
    }
}

impl Drop for Worker {
    fn drop(&mut self) {
        let _ = self.stop.try_send(());
    }
}

/// No shell, no inherited stdout, no unbounded wait. A stuck fontconfig helper is killed.
#[allow(clippy::disallowed_methods)] // This entire module is Linux-only; the native subprocess deadline cannot run on wasm.
fn font_face(pattern: &str) -> Option<FontFace> {
    let mut child = Command::new("fc-match")
        .args(["--format", "%{file}\n%{index}\n", pattern])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .ok()?;
    let deadline = Instant::now() + Duration::from_secs(2);
    loop {
        match child.try_wait() {
            Ok(Some(status)) if status.success() => break,
            Ok(Some(_)) => return None,
            Ok(None) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(20)),
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                return None;
            }
        }
    }
    let mut bytes = Vec::new();
    child.stdout.take()?.take(8193).read_to_end(&mut bytes).ok()?;
    if bytes.len() > 8192 {
        return None;
    }
    let text = std::str::from_utf8(&bytes).ok()?;
    let mut lines = text.lines();
    let path = PathBuf::from(lines.next()?);
    if !path.is_absolute() {
        return None;
    }
    let index = lines.next()?.parse().ok()?;
    let bytes = files::read_bounded(&path, FONT_LIMIT)?;
    use skrifa::MetadataProvider;
    if !skrifa::FontRef::from_index(&bytes, index).is_ok_and(|font| font.charmap().has_map()) {
        return None;
    }
    Some(FontFace { bytes: Arc::new(bytes), index })
}
