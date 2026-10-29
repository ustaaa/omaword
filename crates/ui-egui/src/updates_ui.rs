//! OmaWord updates are installation-managed; never query/install an upstream WordCraft build.
use crate::WordApp;
#[derive(Default)]
pub(crate) struct Runtime {
    pub(crate) manual_window_open: bool,
    pub(crate) status_message: Option<String>,
}
impl WordApp {
    /// Compatibility hook; the fork has no unattended in-process updater.
    pub fn set_startup_update_check(&mut self, _on: bool) {}
}
pub(crate) fn check(app: &mut WordApp) {
    app.updates_rt.manual_window_open = true;
    app.updates_rt.status_message = Some(tl!("OmaWord updates are managed by your installation.").to_string());
}
pub(crate) fn tick(_app: &mut WordApp, _ctx: &egui::Context) {}
pub(crate) fn show(app: &mut WordApp, ctx: &egui::Context) {
    if app.updates_rt.manual_window_open {
        let mut open = true;
        let mut close = false;
        egui::Window::new(tl!("Check for Updates"))
            .open(&mut open)
            .resizable(false)
            .collapsible(false)
            .anchor(egui::Align2::CENTER_CENTER, egui::vec2(0.0, 0.0))
            .show(ctx, |ui| {
                if let Some(msg) = &app.updates_rt.status_message {
                    ui.label(msg);
                } else {
                    ui.label(tl!("Checking for updates…"));
                }
                ui.add_space(8.0);
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.button(tl!("Close")).clicked() {
                        close = true;
                    }
                });
            });
        if !open || close {
            app.updates_rt.manual_window_open = false;
            app.updates_rt.status_message = None;
        }
    }
}
