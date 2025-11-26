use std::path::Path;

/// Trait for detecting and validating audio recordings from different console formats
pub trait ConsoleFormat {
    /// Returns true if the given path matches this console's recording format
    fn matches(&self, path: &Path) -> bool;

    /// Returns a human-readable name for this console format
    fn name(&self) -> &'static str;
}

/// Behringer X32 console format (e.g., "R_2025-01-15_14-30-00.WAV")
pub struct BehringerX32;

impl ConsoleFormat for BehringerX32 {
    fn matches(&self, path: &Path) -> bool {
        if path.extension().and_then(|ext| ext.to_str()) != Some("wav") {
            return false;
        }

        path.file_name()
            .and_then(|name| name.to_str())
            .map_or(false, |name| name.starts_with("R_"))
    }

    fn name(&self) -> &'static str {
        "Behringer X32"
    }
}

/// Allen & Heath CQ series format (e.g., "AHCQ/USBREC/CQ-ST001.WAV")
pub struct AllenHeathCQ;

impl ConsoleFormat for AllenHeathCQ {
    fn matches(&self, path: &Path) -> bool {
        if path.extension().and_then(|ext| ext.to_str()) != Some("WAV") {
            return false;
        }

        // Check if path contains AHCQ/USBREC/ and filename starts with CQ-ST
        let path_str = path.to_string_lossy();
        if !path_str.contains("AHCQ") || !path_str.contains("USBREC") {
            return false;
        }

        path.file_name()
            .and_then(|name| name.to_str())
            .map_or(false, |name| name.starts_with("CQ-ST"))
    }

    fn name(&self) -> &'static str {
        "Allen & Heath CQ"
    }
}

/// Returns all supported console formats
pub fn all_formats() -> Vec<Box<dyn ConsoleFormat>> {
    vec![Box::new(BehringerX32), Box::new(AllenHeathCQ)]
}

/// Checks if a path matches any supported console format
pub fn is_valid_recording(path: &Path) -> bool {
    all_formats().iter().any(|format| format.matches(path))
}
