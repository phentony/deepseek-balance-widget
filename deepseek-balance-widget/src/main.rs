#![windows_subsystem = "windows"]

use std::fs;
use std::path::PathBuf;
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

use eframe::egui;
use reqwest::blocking::Client;
use serde::{Deserialize, Serialize};
use chrono::Local;

// ── Config ──────────────────────────────────────────────────

#[derive(Serialize, Deserialize)]
struct ConfigData {
    api_key: Option<String>,
    refresh_interval: u64,
}

impl Default for ConfigData {
    fn default() -> Self {
        Self { api_key: None, refresh_interval: 300 }
    }
}

fn config_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_default()
        .join(".deepseek-widget")
        .join("config.json")
}

fn load_config() -> ConfigData {
    let path = config_path();
    if path.exists() {
        fs::read_to_string(&path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    } else {
        ConfigData::default()
    }
}

fn save_config(data: &ConfigData) {
    let path = config_path();
    if let Some(dir) = path.parent() {
        fs::create_dir_all(dir).ok();
    }
    fs::write(&path, serde_json::to_string_pretty(data).unwrap_or_default()).ok();
}

// ── API ─────────────────────────────────────────────────────

#[derive(Deserialize)]
struct BalanceResponse {
    is_available: bool,
    balance_infos: Vec<BalanceInfoRaw>,
}

#[derive(Deserialize)]
struct BalanceInfoRaw {
    currency: String,
    total_balance: String,
    granted_balance: String,
    topped_up_balance: String,
}

struct BalanceInfo {
    #[allow(dead_code)]
    is_available: bool,
    currency: String,
    total_balance: f64,
    granted_balance: f64,
    topped_up_balance: f64,
}

fn fetch_balance(api_key: &str) -> Result<BalanceInfo, String> {
    let client = Client::new();
    let resp = client
        .get("https://api.deepseek.com/user/balance")
        .header("Accept", "application/json")
        .header("Authorization", format!("Bearer {}", api_key))
        .timeout(Duration::from_secs(10))
        .send()
        .map_err(|e| format!("network error: {}", e))?;

    if resp.status() == 401 {
        return Err("invalid API key (401)".into());
    }
    if !resp.status().is_success() {
        let status = resp.status();
        let detail = resp.text().unwrap_or_default();
        let short = if detail.len() > 100 { &detail[..100] } else { &detail };
        return Err(format!("API error: HTTP {} {}", status, short));
    }

    let data: BalanceResponse = resp.json().map_err(|e| format!("parse error: {}", e))?;
    let bi = data.balance_infos.iter()
        .find(|b| b.total_balance.parse::<f64>().unwrap_or(0.0) > 0.0)
        .unwrap_or(&data.balance_infos[0]);

    Ok(BalanceInfo {
        is_available: data.is_available,
        currency: bi.currency.clone(),
        total_balance: bi.total_balance.parse().unwrap_or(0.0),
        granted_balance: bi.granted_balance.parse().unwrap_or(0.0),
        topped_up_balance: bi.topped_up_balance.parse().unwrap_or(0.0),
    })
}

// ── Tray Messages ───────────────────────────────────────────

enum TrayCmd {
    Toggle,
    Refresh,
    Settings,
    Quit,
}

// ── App State ───────────────────────────────────────────────

struct DeepSeekApp {
    config: ConfigData,
    balance: Option<BalanceInfo>,
    error: Option<String>,
    last_update: Option<chrono::DateTime<chrono::Local>>,
    next_refresh: f64,
    show_settings: bool,
    api_key_input: String,
    interval_input: String,
    first_run: bool,
    window_visible: bool,
    tray_rx: mpsc::Receiver<TrayCmd>,
}

impl DeepSeekApp {
    fn new(config: ConfigData, tray_rx: mpsc::Receiver<TrayCmd>, first_run: bool) -> Self {
        let mut app = Self {
            config,
            balance: None,
            error: None,
            last_update: None,
            next_refresh: 0.0,
            show_settings: first_run,
            api_key_input: String::new(),
            interval_input: String::new(),
            first_run,
            window_visible: true,
            tray_rx,
        };
        if !first_run {
            app.do_refresh();
        }
        app
    }

    fn do_refresh(&mut self) {
        if let Some(ref key) = self.config.api_key {
            match fetch_balance(key) {
                Ok(info) => {
                    self.balance = Some(info);
                    self.error = None;
                    self.last_update = Some(Local::now());
                }
                Err(e) => {
                    self.error = Some(e);
                }
            }
        } else {
            self.error = Some("no API key configured".into());
        }
    }
}

impl eframe::App for DeepSeekApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Drain tray commands
        while let Ok(cmd) = self.tray_rx.try_recv() {
            match cmd {
                TrayCmd::Toggle => {
                    self.window_visible = !self.window_visible;
                    ctx.send_viewport_cmd(egui::ViewportCommand::Visible(self.window_visible));
                }
                TrayCmd::Refresh => self.do_refresh(),
                TrayCmd::Settings => {
                    self.api_key_input = self.config.api_key.clone().unwrap_or_default();
                    self.interval_input = self.config.refresh_interval.to_string();
                    self.show_settings = true;
                }
                TrayCmd::Quit => std::process::exit(0),
            }
        }

        // Auto-refresh timer
        let now = ctx.input(|i| i.time);
        if now >= self.next_refresh && !self.first_run {
            self.do_refresh();
            self.next_refresh = now + self.config.refresh_interval as f64;
        }

        // ── Settings Dialog ──
        if self.show_settings {
            egui::Window::new("Settings")
                .collapsible(false)
                .resizable(false)
                .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
                .show(ctx, |ui| {
                    ui.set_min_width(300.0);
                    ui.horizontal(|ui| {
                        ui.label("API Key: ");
                        ui.add_sized([180.0, 20.0], egui::TextEdit::singleline(&mut self.api_key_input).password(true));
                    });
                    ui.add_space(8.0);
                    ui.horizontal(|ui| {
                        ui.label("Refresh (seconds, 30-3600): ");
                        ui.add_sized([50.0, 20.0], egui::TextEdit::singleline(&mut self.interval_input));
                    });
                    ui.add_space(16.0);
                    ui.horizontal(|ui| {
                        if ui.button("Cancel").clicked() {
                            self.show_settings = false;
                            if self.first_run {
                                std::process::exit(0);
                            }
                        }
                        ui.add_space(8.0);
                        let can_save = !self.api_key_input.trim().is_empty();
                        if can_save {
                            if ui.button("Save").clicked() {
                                self.config.api_key = Some(self.api_key_input.trim().into());
                                if let Ok(v) = self.interval_input.parse::<u64>() {
                                    self.config.refresh_interval = v.clamp(30, 3600);
                                }
                                save_config(&self.config);
                                self.show_settings = false;
                                self.first_run = false;
                                self.do_refresh();
                                self.next_refresh = ctx.input(|i| i.time) + self.config.refresh_interval as f64;
                            }
                        } else {
                            ui.add_enabled(false, egui::Button::new("Save"));
                        }
                    });
                });
            ctx.request_repaint();
            return;
        }

        // ── Main Panel ──
        let panel_frame = egui::Frame::default()
            .fill(egui::Color32::from_rgb(10, 10, 10))
            .inner_margin(egui::vec2(16.0, 16.0));

        egui::CentralPanel::default().frame(panel_frame).show(ctx, |ui| {
            // Title bar
            ui.horizontal(|ui| {
                ui.label(
                    egui::RichText::new("DeepSeek")
                        .color(egui::Color32::from_rgb(130, 130, 130))
                        .size(11.0),
                );
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.add(
                        egui::Button::new(
                            egui::RichText::new("X").color(egui::Color32::WHITE).size(14.0)
                        )
                        .fill(egui::Color32::from_rgb(70, 30, 30))
                        .small()
                    ).clicked() {
                        ctx.send_viewport_cmd(egui::ViewportCommand::Visible(false));
                    }
                });
            });
            // Drag: any mouse-down + movement = drag window
            let ptr = ctx.input(|i| i.pointer.clone());
            if ptr.button_down(egui::PointerButton::Primary) && ptr.delta().length_sq() > 1.0 {
                ctx.send_viewport_cmd(egui::ViewportCommand::StartDrag);
            }

            ui.add_space(6.0);

            // Error
            if let Some(ref err) = self.error {
                ui.label(
                    egui::RichText::new(err)
                        .color(egui::Color32::from_rgb(255, 90, 90))
                        .size(10.0),
                );
                ui.add_space(4.0);
            }

            // Balance
            if let Some(ref info) = self.balance {
                let color = if info.total_balance > 1.0 {
                    egui::Color32::from_rgb(100, 220, 100)
                } else {
                    egui::Color32::from_rgb(255, 90, 90)
                };
                ui.label(
                    egui::RichText::new(format!("{:.2}", info.total_balance))
                        .color(color)
                        .size(40.0),
                );
                ui.label(
                    egui::RichText::new(&info.currency)
                        .color(egui::Color32::from_rgb(140, 140, 140))
                        .size(12.0),
                );
                ui.add_space(8.0);
                ui.columns(2, |cols| {
                    cols[0].label(
                        egui::RichText::new("Granted")
                            .color(egui::Color32::from_rgb(120, 120, 120))
                            .size(11.0),
                    );
                    cols[0].label(
                        egui::RichText::new(format!("{:.2}", info.granted_balance))
                            .color(egui::Color32::from_rgb(180, 180, 180))
                            .size(17.0),
                    );
                    cols[1].label(
                        egui::RichText::new("Topped Up")
                            .color(egui::Color32::from_rgb(120, 120, 120))
                            .size(11.0),
                    );
                    cols[1].label(
                        egui::RichText::new(format!("{:.2}", info.topped_up_balance))
                            .color(egui::Color32::from_rgb(180, 180, 180))
                            .size(17.0),
                    );
                });
            } else if self.error.is_none() {
                ui.label(
                    egui::RichText::new("--.--")
                        .color(egui::Color32::from_rgb(100, 220, 100))
                        .size(40.0),
                );
            }

            // Footer
            ui.with_layout(egui::Layout::bottom_up(egui::Align::LEFT), |ui| {
                if let Some(ref t) = self.last_update {
                    ui.label(
                        egui::RichText::new(format!("Updated {}", t.format("%H:%M:%S")))
                            .color(egui::Color32::from_rgb(70, 70, 70))
                            .size(10.0),
                    );
                }
            });
        });

        ctx.request_repaint_after(Duration::from_secs(1));
    }
}

// ── Tray Icon Thread ────────────────────────────────────────

fn start_tray(tx: mpsc::Sender<TrayCmd>) {
    thread::spawn(move || {
        use tray_icon::{
            TrayIconBuilder,
            menu::{Menu, MenuEvent, MenuItemBuilder},
            Icon,
        };

        // Build 32x32 RGBA icon: green ring with dark center
        let mut pixels = vec![0u8; 32 * 32 * 4];
        for y in 0..32i32 {
            for x in 0..32i32 {
                let dx = x - 16;
                let dy = y - 16;
                let d2 = dx * dx + dy * dy;
                let idx = ((y * 32 + x) * 4) as usize;
                if d2 <= 144 && d2 > 36 {
                    // green ring
                    pixels[idx] = 166;
                    pixels[idx + 1] = 227;
                    pixels[idx + 2] = 161;
                    pixels[idx + 3] = 255;
                } else if d2 <= 36 {
                    // dark center
                    pixels[idx] = 30;
                    pixels[idx + 1] = 30;
                    pixels[idx + 2] = 46;
                    pixels[idx + 3] = 255;
                }
            }
        }

        let icon = Icon::from_rgba(pixels, 32, 32).expect("icon from rgba");

        let menu = Menu::new();
        menu.append(&MenuItemBuilder::new().text("Show/Hide").enabled(true).build()).ok();
        menu.append(&MenuItemBuilder::new().text("Refresh Now").enabled(true).build()).ok();
        menu.append(&tray_icon::menu::PredefinedMenuItem::separator()).ok();
        menu.append(&MenuItemBuilder::new().text("Settings...").enabled(true).build()).ok();
        menu.append(&tray_icon::menu::PredefinedMenuItem::separator()).ok();
        menu.append(&MenuItemBuilder::new().text("Quit").enabled(true).build()).ok();

        let _tray = TrayIconBuilder::new()
            .with_icon(icon)
            .with_menu(Box::new(menu))
            .with_tooltip("DeepSeek Balance")
            .build()
            .expect("tray icon");

        // Listen for menu events
        loop {
            if let Ok(event) = MenuEvent::receiver().recv() {
                let cmd = match event.id.0.as_str() {
                    "Show/Hide" => TrayCmd::Toggle,
                    "Refresh Now" => TrayCmd::Refresh,
                    "Settings..." => TrayCmd::Settings,
                    "Quit" => TrayCmd::Quit,
                    _ => continue,
                };
                tx.send(cmd).ok();
            }
        }
    });
}

// ── Main ────────────────────────────────────────────────────

fn main() {
    let config = load_config();
    let first_run = config.api_key.is_none();

    let (tray_tx, tray_rx) = mpsc::channel();
    start_tray(tray_tx);

    let app = DeepSeekApp::new(config, tray_rx, first_run);

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([300.0, 220.0])
            .with_decorations(false)
            .with_always_on_top()
            .with_resizable(false)
            .with_transparent(false)
            .with_taskbar(false),
        ..Default::default()
    };

    eframe::run_native(
        "DeepSeek Balance",
        options,
        Box::new(|_cc| Ok(Box::new(app))),
    )
    .ok();
}
