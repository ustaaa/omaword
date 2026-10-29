//! Transient desktop chrome; document rendering and document font families stay unchanged.
use super::{Color32, FontDefinitions, FontFamily, Tokens};
use crate::omarchy::{FontFace, Palette, blend};
fn palette_id() -> egui::Id {
    egui::Id::unique("omaword.appearance.palette")
}
fn fonts_id() -> egui::Id {
    egui::Id::unique("omaword.appearance.fonts")
}
fn base_fonts_id() -> egui::Id {
    egui::Id::unique("omaword.appearance.base-fonts")
}

/// Store a UI-only palette. The caller reapplies its effective appearance when this changes.
pub fn set_omarchy_palette(ctx: &egui::Context, palette: Option<Palette>) -> bool {
    if ctx.data(|d| d.get_temp::<Palette>(palette_id())) == palette {
        return false;
    }
    ctx.data_mut(|d| {
        if let Some(p) = palette {
            d.insert_temp(palette_id(), p);
        } else {
            d.remove::<Palette>(palette_id());
        }
    });
    ctx.request_repaint();
    true
}

pub(super) fn resolved(ctx: &egui::Context, dark: bool) -> Tokens {
    let mut t = if dark { Tokens::dark() } else { Tokens::light() };
    let Some(p) = ctx.data(|d| d.get_temp::<Palette>(palette_id())).filter(|p| p.dark == dark) else {
        return t;
    };
    t.title_bar = p.background;
    t.ribbon = p.surface;
    t.tab_strip = p.background;
    t.canvas = p.background;
    t.panel = p.surface;
    t.menu = p.surface;
    t.input = p.background;
    t.text = readable(p.foreground, p.surface, 4.5);
    t.text_dim = readable(p.muted, p.surface, 4.5);
    t.text_disabled = blend(p.surface, t.text, 0.45);
    t.icon = t.text;
    t.group_label = t.text_dim;
    t.accent = readable(p.accent, p.surface, 3.0);
    t.accent_text = readable(p.accent, p.surface, 4.5);
    t.on_accent = readable(p.background, t.accent, 4.5);
    // Backstage's white-on-blue sidebar remains readable under every selected palette.
    t.nav = if contrast(Color32::WHITE, p.accent) >= 4.5 { p.accent } else { p.background };
    if contrast(Color32::WHITE, t.nav) < 4.5 {
        t.nav = Color32::from_rgb(0x28, 0x28, 0x28);
    }
    t.border = blend(p.surface, t.text, 0.22);
    t.border_strong = blend(p.surface, t.text, 0.4);
    t.input_border = t.border;
    t.hover = blend(p.surface, t.text, 0.08);
    t.pressed = blend(p.surface, t.text, 0.14);
    t.checked = p.selection;
    t.ruler = p.surface;
    t.ruler_margin = p.background;
    t.ruler_tick = t.text;
    t.status_bar = p.background;
    // Paper, selection, find marks, handles, guides, equation/crop ink and author colours
    // retain upstream values; these belong to document drawing/interaction.
    t
}
fn contrast(a: Color32, b: Color32) -> f32 {
    let luminance = |c: Color32| {
        let linear = |v: u8| {
            let v = f32::from(v) / 255.0;
            if v <= 0.04045 { v / 12.92 } else { ((v + 0.055) / 1.055).powf(2.4) }
        };
        0.2126 * linear(c.r()) + 0.7152 * linear(c.g()) + 0.0722 * linear(c.b())
    };
    let (a, b) = (luminance(a), luminance(b));
    (a.max(b) + 0.05) / (a.min(b) + 0.05)
}
fn readable(color: Color32, bg: Color32, ratio: f32) -> Color32 {
    if contrast(color, bg) >= ratio {
        return color;
    }
    let target = if contrast(Color32::WHITE, bg) > contrast(Color32::BLACK, bg) { Color32::WHITE } else { Color32::BLACK };
    for i in 1..=20 {
        let c = blend(color, target, i as f32 / 20.0);
        if contrast(c, bg) >= ratio {
            return c;
        }
    }
    target
}
pub(crate) fn set_omarchy_fonts(ctx: &egui::Context, fonts: Option<(FontFace, FontFace)>) -> bool {
    let previous = ctx.data(|d| d.get_temp::<(FontFace, FontFace)>(fonts_id()));
    if previous == fonts {
        return false;
    }
    ctx.data_mut(|d| {
        if let Some(fonts) = fonts {
            d.insert_temp(fonts_id(), fonts);
        } else {
            d.remove::<(FontFace, FontFace)>(fonts_id());
        }
    });
    true
}

/// Reuse the exact current document font set; a chrome refresh must never rerun discovery,
/// clear the bound-family registry, or briefly display workbook fallback faces.
pub(crate) fn refresh_omarchy_fonts(ctx: &egui::Context, fonts: Option<(FontFace, FontFace)>) -> bool {
    if ctx.data(|d| d.get_temp::<(FontFace, FontFace)>(fonts_id())) == fonts {
        return false;
    }
    let Some(base) = ctx.data(|d| d.get_temp::<FontDefinitions>(base_fonts_id())) else { return false };
    set_omarchy_fonts(ctx, fonts);
    ctx.set_fonts(with_omarchy_fonts(ctx, base));
    true
}

/// Prefix only UI roles; CELL/MONO/SERIF and workbook-specific chains remain byte-for-byte intact.
pub(crate) fn with_omarchy_fonts(ctx: &egui::Context, mut fonts: FontDefinitions) -> FontDefinitions {
    ctx.data_mut(|d| d.insert_temp(base_fonts_id(), fonts.clone()));
    if let Some((normal, bold)) = ctx.data(|d| d.get_temp::<(FontFace, FontFace)>(fonts_id())) {
        for (role, face) in [("omaword-ui", normal.clone()), ("omaword-medium", bold.clone()), ("omaword-semibold", bold)] {
            let key = format!("{role}-face");
            let blob: egui::epaint::text::Blob = face.bytes;
            fonts.font_data.insert(key.clone(), std::sync::Arc::new(egui::FontData::from_blob(blob, face.index)));
            fonts.families.entry(FontFamily::Name(role.into())).or_default().insert(0, key);
        }
    }
    fonts
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn palette_changes_only_chrome_and_restores_exact_original() {
        let ctx = egui::Context::default();
        for dark in [false, true] {
            let base = if dark { Tokens::dark() } else { Tokens::light() };
            let palette = Palette {
                dark,
                background: Color32::from_rgb(22, 25, 30),
                foreground: Color32::WHITE,
                accent: Color32::from_rgb(220, 175, 50),
                selection: Color32::GRAY,
                muted: Color32::GRAY,
                surface: Color32::from_rgb(32, 35, 40),
            };
            assert!(set_omarchy_palette(&ctx, Some(palette)));
            let t = resolved(&ctx, dark);
            assert_eq!(t.ribbon, palette.surface);
            assert_eq!(
                (t.selection, t.find_highlight, t.guide, t.equation_box, t.leader_colors),
                (base.selection, base.find_highlight, base.guide, base.equation_box, base.leader_colors)
            );
            assert!(set_omarchy_palette(&ctx, None));
            assert_eq!(resolved(&ctx, dark), base);
        }
    }
    #[test]
    fn font_override_preserves_every_original_document_family() {
        let ctx = egui::Context::default();
        let base = super::super::font_definitions(false, false);
        let f = base.font_data.values().next().unwrap();
        let face = FontFace { bytes: std::sync::Arc::new(f.bytes().to_vec()), index: f.index };
        with_omarchy_fonts(&ctx, base.clone());
        assert!(refresh_omarchy_fonts(&ctx, Some((face.clone(), face))));
        let changed = with_omarchy_fonts(&ctx, base.clone());
        for (family, chain) in &base.families {
            if let FontFamily::Name(name) = family
                && name.starts_with("omaword-")
            {
                continue;
            }
            assert_eq!(changed.families.get(family), Some(chain));
        }
        assert_eq!(changed.families[&FontFamily::Name("omaword-ui".into())][0], "omaword-ui-face");
        assert!(refresh_omarchy_fonts(&ctx, None));
        assert_eq!(with_omarchy_fonts(&ctx, base.clone()).families, base.families);
    }
}
