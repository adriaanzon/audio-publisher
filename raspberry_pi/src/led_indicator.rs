use rppal::gpio::{Gpio, OutputPin};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

static LED_PIN: Mutex<Option<OutputPin>> = Mutex::new(None);
static BLINK_THREAD: Mutex<Option<JoinHandle<()>>> = Mutex::new(None);
static BLINK_STOP: AtomicBool = AtomicBool::new(false);
static LED_STATE: Mutex<bool> = Mutex::new(false);

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
        *LED_STATE.lock().unwrap() = true;
    }
}

pub fn turn_off() {
    if let Some(pin) = LED_PIN.lock().unwrap().as_mut() {
        let _ = pin.set_low();
        *LED_STATE.lock().unwrap() = false;
    }
}

fn toggle_led() {
    if let Some(pin) = LED_PIN.lock().unwrap().as_mut() {
        let mut state = LED_STATE.lock().unwrap();
        *state = !*state;
        if *state {
            let _ = pin.set_high();
        } else {
            let _ = pin.set_low();
        }
    }
}

pub fn start_blink(duration_secs: u64) {
    stop_blink();

    BLINK_STOP.store(false, Ordering::Relaxed);

    let handle = thread::spawn(move || {
        let end_time = Instant::now() + Duration::from_secs(duration_secs);

        while Instant::now() < end_time && !BLINK_STOP.load(Ordering::Relaxed) {
            toggle_led();
            thread::sleep(Duration::from_millis(125));
        }

        turn_off();
    });

    *BLINK_THREAD.lock().unwrap() = Some(handle);
}

pub fn stop_blink() {
    BLINK_STOP.store(true, Ordering::Relaxed);
    if let Some(handle) = BLINK_THREAD.lock().unwrap().take() {
        let _ = handle.join();
    }
    turn_off();
}
