//
// Helpers
//
function elById(id) {
    return document.getElementById(id);
}
function toggleVisibility(id) {
    let element = elById("groups-list");
    if (element.style.display == 'none') {
        element.style.display = 'block';
    } else {
        element.style.display = 'none';
    }
}

function makeId(base, name) {
    return base + "_" + name.replace(' ', '_').toLowerCase();
}

//
// App Logic
//
function deviceClicked(device) {
    console.log("Device Clicked" + device);

    let div = elById(device);
    let action = "enable"
    if (div.classList.contains("device_state_on")) 
        action = "disable";
    
    fetch('/api/device/' + device + '/' + action)
        .then(response => updateData())
}

function updateDeviceUi(div, device) {
    let html = "";
    html += '<div class="device_color_overlay_' + device.state + '"></div>';
    html += '<div class="device_label">' + device.name + "</div>"
    div.innerHTML = html;

    div.classList.remove("device_state_on");
    div.classList.remove("device_state_off");

    div.classList.add("device_state_" + device.state);
}

function selectGroup(group) {
    elById("groups-button").textContent = group;
    elById("groups-list").style.display = 'none';
    console.log("Selecting Group " + group);
}

function handleListResponse(data) {
    //console.log(data);

    if (data.status != 'ok') {
        console.log("Call failure: ");
        return;
    }

    let groups_added = 0;

    data.groups.forEach(group => {
        let id = makeId("group", group);
        let element = elById(id);
        if (element == null) {
            element = document.createElement("a");
            element.setAttribute("id", id);

            var groups_list = elById("groups-list");
            groups_list.appendChild(element);

            element.textContent = group
            element.addEventListener("click", () => { selectGroup(group); });
            groups_added += 1;
        }
    });

    data.devices.forEach(device => {
        let div = elById(device.id);
        if (div == null) {
            div = document.createElement("div");
            div.setAttribute("id", device.id);

            var devices_list = elById("devices-list");
            devices_list.appendChild(div);

            div = elById(device.id);
            div.addEventListener("click", () => { deviceClicked(device.id); });
        }
        updateDeviceUi(div, device);
    });


    if (groups_added > 0) {
        selectGroup(data.groups[0]);
    }

    console.log("Update complete.");
}

function updateData() {
    console.log("Fetching data...");
    fetch('/api/device/list')
        .then(response => response.json())
        .then(data => handleListResponse(data));
}

//
// Bootstrap
//
console.log("Initializing");
elById("groups-button").addEventListener("click", () => { toggleVisibility("groups-list"); });
updateData();

