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
fn palette_at(root: &Path) -> Option<Palette> {
    let bytes = read_bounded(&root.join("colors.toml"), MAX_PALETTE)?;
    Palette::parse(std::str::from_utf8(&bytes).ok()?, root.join("light.mode").is_file())
}

/// Keep the selected root until a higher-priority root has a valid palette. Once selected,
/// an invalid or missing palette returns `None` so callers retain their last good snapshot.
pub(super) fn read_palette(roots: &[PathBuf], selected: &mut Option<PathBuf>) -> Option<Palette> {
    if let Some(root) = selected.as_ref() {
        let palette = palette_at(root)?;
        if let Some(index) = roots.iter().position(|candidate| candidate == root) {
            for preferred in &roots[..index] {
                if let Some(palette) = palette_at(preferred) {
                    *selected = Some(preferred.clone());
                    return Some(palette);
                }
            }
        }
        return Some(palette);
    }
    for root in roots {
        if let Some(palette) = palette_at(root) {
            *selected = Some(root.clone());
            return Some(palette);
        }
    }
    None
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
    #[test]
    fn promotes_legacy_root_only_after_preferred_palette_is_valid() {
        let base = std::env::temp_dir().join(format!("omaword-theme-priority-test-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        let state = base.join("state");
        let legacy = base.join("legacy");
        std::fs::create_dir_all(&state).unwrap();
        std::fs::create_dir_all(&legacy).unwrap();
        std::fs::write(state.join("colors.toml"), "partial=").unwrap();
        std::fs::write(legacy.join("colors.toml"), "background='#eeeeee'\nforeground='#111111'").unwrap();
        let roots = vec![state.clone(), legacy.clone()];
        let mut selected = None;
        let legacy_palette = read_palette(&roots, &mut selected).unwrap();
        assert_eq!(selected.as_deref(), Some(legacy.as_path()));

        std::fs::write(state.join("colors.toml"), "background='#101010'\nforeground='#ffffff'").unwrap();
        let state_palette = read_palette(&roots, &mut selected).unwrap();
        assert_ne!(state_palette, legacy_palette);
        assert_eq!(selected.as_deref(), Some(state.as_path()));

        std::fs::write(state.join("colors.toml"), "partial=").unwrap();
        assert!(read_palette(&roots, &mut selected).is_none());
        assert_eq!(selected.as_deref(), Some(state.as_path()));
        std::fs::remove_dir_all(base).unwrap();
    }
}
