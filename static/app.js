function updateDeviceUi(div, device) {
    div.textContent = device.name;
}



function handleListResponse(data) {
    console.log(data);

    if (data.status != 'ok') {
        console.log("Call failure: ");
        return;
    }

    data.groups.forEach(group => {
        let id = "group_" + group.replace(' ', '_').toLowerCase();
        let element = document.getElementById(id);
        if (element == null) {
            element = document.createElement("a");
            element.setAttribute("id", id);

            var groups_list = document.getElementById("groups-list");
            groups_list.appendChild(element);

            element.textContent = group
        }
    });


    data.devices.forEach(device => {
        let div = document.getElementById(device.id);
        if (div == null) {
            div = document.createElement("div");
            div.setAttribute("id", device.id);

            var devices_list = document.getElementById("devices-list");
            devices_list.appendChild(div);

            div = document.getElementById(device.id);
        }
        updateDeviceUi(div, device);
    });

    console.log("Update complete.");
}

function updateData() {
    console.log("Fetching data...");
    fetch('/api/device/list')
        .then(response => response.json())
        .then(data => handleListResponse(data));
}


console.log("Initializing");
updateData();

