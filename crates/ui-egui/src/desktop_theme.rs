//! Linux appearance through the suite's bounded, cancellable XDG portal subscription.
//! The subscription is lazy: embedders and tests do not touch the desktop unless requested.

#[derive(Default)]
pub struct DesktopTheme {
    started: bool,
    #[cfg(target_os = "linux")]
    watcher: Option<craft_platform::appearance::Watcher>,
    last: Option<bool>,
}

impl DesktopTheme {
    pub fn start() -> Self {
        Self { started: true, ..Self::default() }
    }

    /// Reads only cached state; D-Bus and compatibility fallbacks run in craft-platform's worker.
    pub fn take_change(&mut self, ctx: &egui::Context, active: bool) -> Option<bool> {
        #[cfg(target_os = "linux")]
        {
            if self.started {
                self.started = false;
                let wake = ctx.clone();
                self.watcher = craft_platform::appearance::Watcher::start_active(active, move || wake.request_repaint());
            }
            if let Some(watcher) = &self.watcher {
                watcher.set_active(active);
                let now = watcher.current().map(|theme| theme == craft_platform::appearance::Theme::Dark);
                if now.is_some() && now != self.last {
                    self.last = now;
                    return now;
                }
            }
        }
        #[cfg(not(target_os = "linux"))]
        let _ = (ctx, active, self.started, self.last);
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn unstarted_watcher_never_contacts_the_desktop() {
        assert_eq!(DesktopTheme::default().take_change(&egui::Context::default(), true), None);
    }
}
