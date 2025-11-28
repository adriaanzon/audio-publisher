use rppal::gpio::{Gpio, OutputPin};
use std::sync::Mutex;

static LED_PIN: Mutex<Option<OutputPin>> = Mutex::new(None);

const DEFAULT_PIN: u8 = 17;

pub fn initialize() {
    match Gpio::new().and_then(|gpio| gpio.get(DEFAULT_PIN).map(|p| p.into_output())) {
        Ok(pin) => {
            *LED_PIN.lock().unwrap() = Some(pin);
            println!("LED indicator initialized on GPIO pin {}", DEFAULT_PIN);
        }
        Err(e) => {
            eprintln!("LED indicator not available: {}", e);
            eprintln!("Continuing without LED indicator...");
        }
    }
}

pub fn turn_on() {
    if let Some(pin) = LED_PIN.lock().unwrap().as_mut() {
        let _ = pin.set_high();
    }
}

pub fn turn_off() {
    if let Some(pin) = LED_PIN.lock().unwrap().as_mut() {
        let _ = pin.set_low();
    }
}
