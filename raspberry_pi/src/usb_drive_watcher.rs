use anyhow::Result;
use nix::mount::{mount, umount, MsFlags};

pub async fn watch<F, Fut>(closure: F)
where
    F: Fn(&str) -> Fut,
    Fut: std::future::Future<Output = Result<()>>,
{
    let monitor = udev::MonitorBuilder::new()
        .expect("Failed to monitor usb events")
        .match_subsystem("block")
        .expect("Failed to monitor usb events")
        .listen()
        .expect("Failed to monitor usb events");

    loop {
        match monitor.iter().next() {
            None => {}
            Some(event) => {
                let action = match event.action() {
                    Some(a) => a,
                    None => {
                        eprintln!("Error getting action");
                        continue;
                    }
                };

                let devtype = match event.devtype() {
                    Some(dt) => dt,
                    None => {
                        eprintln!("Error getting devtype");
                        continue;
                    }
                };

                if action != "add" || devtype != "partition" {
                    continue;
                }

                let sysname = match event.sysname().to_str() {
                    Some(s) => s,
                    None => {
                        eprintln!("Error getting sysname");
                        continue;
                    }
                };
                let mount_point = format!("/mnt/{}", sysname);

                // Make directory
                match std::fs::create_dir_all(&mount_point) {
                    Ok(_) => {}
                    Err(e) => {
                        eprintln!("Error creating directory: {}", e);
                        continue;
                    }
                }

                let source = match event.devnode() {
                    Some(s) => s,
                    None => {
                        eprintln!("Error getting devnode");
                        continue;
                    }
                };
                println!(
                    "Attempting to mount device at {:?} to {:?}",
                    source, mount_point
                );

                // Mount
                match mount(
                    Some(source),
                    mount_point.as_str(),
                    Some("vfat"), // todo: detect file system type
                    MsFlags::MS_RDONLY,
                    None::<&str>,
                ) {
                    Ok(_) => {}
                    Err(e) => {
                        eprintln!("Error mounting: {}", e);
                        continue;
                    }
                }

                // No use of `continue` from here, must always unmount

                println!("Mounted");

                match closure(&mount_point).await {
                    Ok(_) => {}
                    Err(e) => eprintln!("Error while executing the watch handler: {}", e),
                }

                // Unmount
                let _ = umount(mount_point.as_str());
                println!("Unmounted");
            }
        }
    }
}
