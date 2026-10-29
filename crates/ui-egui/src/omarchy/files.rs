use super::{MAX_PALETTE, Palette};
use std::io::Read;
use std::path::{Path, PathBuf};

pub(super) fn roots(state: Option<PathBuf>, config: Option<PathBuf>, home: Option<PathBuf>) -> Vec<PathBuf> {
    let absolute = |p: Option<PathBuf>| p.filter(|p| p.is_absolute());
    let state = absolute(state).or_else(|| home.as_ref().map(|h| h.join(".local/state")));
    let config = absolute(config).or_else(|| home.map(|h| h.join(".config")));
    state.into_iter().chain(config).map(|p| p.join("omarchy/current/theme")).collect()
}

pub(super) fn read_bounded(path: &Path, limit: usize) -> Option<Vec<u8>> {
    // Refuse directories/devices/FIFOs before opening; check again after following a symlink.
    let before = path.metadata().ok()?;
    if !before.is_file() || before.len() > limit as u64 {
        return None;
    }
    let file = std::fs::File::open(path).ok()?;
    let meta = file.metadata().ok()?;
    if !meta.is_file() || meta.len() > limit as u64 {
        return None;
    }
    let mut bytes = Vec::new();
    file.take(limit as u64 + 1).read_to_end(&mut bytes).ok()?;
    (bytes.len() <= limit).then_some(bytes)
}

/// Select the highest-priority active root once. A broken/incomplete v4 update must not
/// temporarily flash an old v3 palette. Both files and directory symlinks are re-read each poll.
pub(super) fn read_palette(roots: &[PathBuf], selected: &mut Option<PathBuf>) -> Option<Palette> {
    if selected.is_none() {
        *selected = roots.iter().find(|p| p.join("colors.toml").is_file()).cloned();
    }
    let root = selected.as_ref()?;
    let bytes = read_bounded(&root.join("colors.toml"), MAX_PALETTE)?;
    Palette::parse(std::str::from_utf8(&bytes).ok()?, root.join("light.mode").is_file())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn xdg_paths_and_relative_values_follow_the_spec() {
        assert_eq!(
            roots(Some("/state".into()), Some("/config".into()), Some("/home/test".into())),
            vec![PathBuf::from("/state/omarchy/current/theme"), PathBuf::from("/config/omarchy/current/theme")]
        );
        assert_eq!(
            roots(Some("relative".into()), None, Some("/home/test".into()))[0],
            PathBuf::from("/home/test/.local/state/omarchy/current/theme")
        );
        assert!(roots(None, None, None).is_empty());
    }
    #[test]
    fn failed_reload_leaves_the_last_good_palette_available() {
        let base = std::env::temp_dir().join(format!("omaword-theme-test-{}", std::process::id()));
        let root = base.join("theme");
        std::fs::create_dir_all(&root).unwrap();
        std::fs::write(root.join("colors.toml"), "background='#101010'\nforeground='#ffffff'").unwrap();
        let mut selected = None;
        let first = read_palette(std::slice::from_ref(&root), &mut selected).unwrap();
        std::fs::remove_file(root.join("colors.toml")).unwrap();
        assert!(read_palette(std::slice::from_ref(&root), &mut selected).is_none());
        std::fs::write(root.join("colors.toml"), "partial=").unwrap();
        assert!(read_palette(std::slice::from_ref(&root), &mut selected).is_none());
        std::fs::write(root.join("colors.toml"), "background='#eeeeee'\nforeground='#111111'").unwrap();
        assert_ne!(read_palette(std::slice::from_ref(&root), &mut selected).unwrap(), first);
        std::fs::remove_dir_all(base).unwrap();
    }
}
