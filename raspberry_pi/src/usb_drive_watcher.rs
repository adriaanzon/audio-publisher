use nix::mount::{mount, unmount, MntFlags};

pub fn watch<F>(closure: F)
where
    F: Fn(&str),
{
    let mut monitor = udev::MonitorBuilder::new()
        .unwrap()
        .match_subsystem("block")
        .unwrap()
        .listen()
        .unwrap();

    loop {
        match monitor.iter().next() {
            None => {}
            Some(event) => {
                let action = match event.action() {
                    Ok(a) => a,
                    Err(e) => {
                        eprintln!("Error getting action: {}", e);
                        continue;
                    }
                };

                let devtype = match event.devtype() {
                    Ok(dt) => dt,
                    Err(e) => {
                        eprintln!("Error getting devtype: {}", e);
                        continue;
                    }
                };

                if action != "add" || devtype != "partition" {
                    continue;
                }

                let mount_point = format!("/mnt/{}", event.sysname());

                // Make directory
                match std::fs::create_dir_all(&mount_point) {
                    Ok(_) => {}
                    Err(e) => {
                        eprintln!("Error creating directory: {}", e);
                        continue;
                    }
                }

                // Mount
                match mount(
                    event.devpath(),
                    mount_point.as_str(),
                    MntFlags::MNT_RDONLY,
                    None,
                ) {
                    Ok(_) => {}
                    Err(e) => {
                        eprintln!("Error mounting: {}", e);
                        continue;
                    }
                }

                // No use of `continue` from here, must always unmount

                println!("Mounted {} at {}", event.devpath(), mount_point);

                if let Err(e) = closure(&mount_point) {
                    eprintln!("Error while executing the watch handler: {}", e);
                }

                // Unmount
                let _ = unmount(mount_point.as_str(), MntFlags::empty());
            }
        }
    }
}
