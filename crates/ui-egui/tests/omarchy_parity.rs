//! Appearance is session UI state, never a document edit or a page-layout change.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use serde_json::{Value, json};
use wordcraft_engine::Session;
use wordcraft_ui_egui::{Services, WordApp, omarchy::Palette, theme};

struct State {
    app: WordApp,
    palette: Option<Palette>,
    dark: bool,
}

#[derive(Debug, PartialEq)]
struct Snapshot {
    document: Value,
    revision: u64,
    dirty: bool,
    undo_depth: usize,
    can_redo: bool,
    pixels: Vec<Vec<u8>>,
}

fn snapshot(app: &mut WordApp) -> Snapshot {
    let pages = app.session.layout().pages.clone();
    let pixels = pages.iter().map(|page| wordcraft_render::render_page(&app.session.doc, page, 0.5, &Default::default()).pixels).collect();
    Snapshot {
        document: serde_json::to_value(&app.session.doc).unwrap(),
        revision: app.session.rev(),
        dirty: app.session.dirty,
        undo_depth: app.session.undo_depth(),
        can_redo: app.session.can_redo(),
        pixels,
    }
}

#[test]
fn palette_switches_preserve_document_history_and_rendered_pages() {
    let mut app = WordApp::new(Session::new(wordcraft_doc::Document::from_text("Oma suite\nİstanbul, çalışma\nFormatted text")), Services::default());
    app.ui.language = "en".into();
    app.run("select.text", json!({"text": "Formatted"})).unwrap();
    app.run("format.bold", json!({})).unwrap();
    let mut h = egui_kittest::Harness::builder().with_size(egui::vec2(1280.0, 800.0)).build_ui_state(
        |ui, state: &mut State| {
            state.app.logic(ui.ctx());
            // Tests have no desktop worker. Inject the same public appearance boundary after
            // logic, before painting, so this exercises a real complete UI pass.
            theme::set_omarchy_palette(ui.ctx(), state.palette);
            theme::apply(ui.ctx(), if state.dark { theme::Appearance::Dark } else { theme::Appearance::Light });
            state.app.ui(ui);
        },
        State { app, palette: None, dark: false },
    );
    h.run_steps(4);
    let before = snapshot(&mut h.state_mut().app);
    for text in [
        "mode='dark'\nbackground='#101020'\nforeground='#eeeeff'\naccent='#aabbff'",
        "mode='light'\nbackground='#fafafa'\nforeground='#222222'\naccent='#224488'",
    ] {
        let palette = Palette::parse(text, false).unwrap();
        h.state_mut().palette = Some(palette);
        h.state_mut().dark = palette.dark;
        h.run_steps(2);
        assert_eq!(snapshot(&mut h.state_mut().app), before, "palette must not touch model, history or page pixels");
    }
    h.state_mut().palette = None;
    h.run_steps(2);
    assert_eq!(snapshot(&mut h.state_mut().app), before, "removing desktop appearance restores chrome without a document edit");
    h.state_mut().app.run("edit.undo", json!({})).unwrap();
    assert!(h.state().app.session.can_redo(), "appearance changes must not consume the formatting undo");
    h.state_mut().app.run("edit.redo", json!({})).unwrap();
    assert_eq!(serde_json::to_value(&h.state().app.session.doc).unwrap(), before.document);
}
