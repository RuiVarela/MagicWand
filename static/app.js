var lastRefresh = new Date();
let refreshInterval = 2500; //ms

//
// Helpers
//
function elById(id) { return document.getElementById(id); }
function elByCls(cls) { return document.getElementsByClassName(cls); }
function makeId(base, name) { return base + "_" + name.replace(' ', '_').toLowerCase(); }

function homeGroup() { return "Home"; }
function dashboardGroup() { return "Dashboard"; }
function showGroupName(group) { return (group == homeGroup()) || (group == dashboardGroup()); }

//
// App Logic
//
function deviceClicked(device, action) {
    let div = elById(device);

    if (action == null) {
        action = "enable"
        if (div.classList.contains("device_state_on"))
            action = "disable";
    }

    console.log("Device Clicked: " + device + " > " + action);

    fetch('/api/device/' + device + '/' + action)
        .then(response => updateData())
}


function updateDeviceUi(div, device) {
    div.device = device;

    let group = device.group;
    let name = device.name;
    if (name.startsWith(group + " "))
        name = name.substring(group.length + 1);
    
    let statePrefix = 'device_state_';
    let nextState = statePrefix + device.state;
    if (div.classList.contains(nextState))
        return;

    let html = "";
    if (device.type == 'curtain') {
        html += '<div class="device_curtain_overlay">';
        html += '   <div class="curtain_open"></div>';
        html += '   <div class="curtain_stop"></div>';
        html += '   <div class="curtain_close"></div>';
        html += '</div>';
    } else {
        html += '<div class="device_color_overlay_' + device.state + '"></div>';
    }

    html += '<div class="device_label">'
    if (group != homeGroup()) {
        let selected_group = elById("groups-button").textContent;
        let toggler = showGroupName(selected_group) ? "showInline" : "hide";
        html += '<span class="device_group ' + toggler + '">' + group + ' </span>'
    }
    html += name + "</div>"
    div.innerHTML = html;

    let remove = [];
    div.classList.forEach(value => {
        if (value.startsWith(statePrefix))
            remove.push(value);
    });

    remove.forEach(value => {
        div.classList.remove(value);
    });
    
    div.classList.add("device_state_" + device.state);


    if (device.type == 'curtain') {
        div.querySelector(`[class=curtain_open]`)
            .addEventListener("click", () => { deviceClicked(device.id, "open"); });

        div.querySelector(`[class=curtain_stop]`)
            .addEventListener("click", () => { deviceClicked(device.id, "stop"); });

        div.querySelector(`[class=curtain_close]`)
            .addEventListener("click", () => { deviceClicked(device.id, "close"); });

    } else {
        if (div.store_click_handler)
            div.removeEventListener("click", div.store_click_handler);

        div.store_click_handler = () => { deviceClicked(device.id, null); };
        div.addEventListener("click", div.store_click_handler);
    }
}

function selectGroup(group, canPushHistory) {
    console.log("Selecting Group " + group);
    elById("groups-button").textContent = group;
    var elements = elById("devices-list");
    elements.childNodes.forEach(div => {
        if (div.device.group == group || 
            group == homeGroup() || 
            (group == dashboardGroup() && div.device.dashboard)) {
            div.style.display = 'block';
        } else {
            div.style.display = 'none';
        }
    });

    let addElement = showGroupName(group) ? "showInline" : "hide";
    let removeElement = showGroupName(group) ? "hide" : "showInline";
    elements = elByCls("device_group");
    for (let i = 0; i != elements.length; ++i) {
        let span = elements[i];
        if (span.classList.contains(removeElement))
            span.classList.remove(removeElement);

        if (!span.classList.contains(removeElement))
            span.classList.add(addElement);
    }

    if (canPushHistory) {
        let current = (location.hash.length == 0) ? "" : location.hash;
        if (current != group) 
            history.pushState("", document.title, window.location.pathname + "#" + group);  
    }
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
            element.addEventListener("click", () => { selectGroup(group, true); });
            
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
        }
        updateDeviceUi(div, device);
    });

    if (groups_added > 0) {
        let selection = data.groups[0];

        if (location.hash.length > 0) 
            selection = decodeURI(location.hash.substring(1));
        selectGroup(selection, true);
    }

    console.log("Update complete.");
}

function updateData() {
    console.log("Fetching data...");
    lastRefresh = new Date();
    fetch('/api/device/list')
        .then(response => response.json())
        .then(data => handleListResponse(data));
}

function periodicUpdates() {

    let now = new Date();
    var ms = now - lastRefresh; //in ms
    if (ms > refreshInterval) 
        updateData();
}

//
// Bootstrap
//
console.log("Initializing");

window.onpopstate = function(event) {

    if (location.hash.length > 0) {
        let selection = decodeURI(location.hash.substring(1));
        selectGroup(selection, false);
    } 

};

// Close the dropdown menu if the user clicks outside of it
window.onclick = function (event) {
    if (!event.target.matches('.dropbtn') && !event.target.matches('.dropdown')) {
        let dropdowns = elByCls("dropdown-content");
        for (let i = 0; i < dropdowns.length; i++) {
            var openDropdown = dropdowns[i];

            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
                openDropdown.classList.add('hide');
            }

        }
    }
}

elById("groups-list").classList.add("hide");
elById("settings-list").classList.add("hide");

elById("groups-button").addEventListener("click", () => { 
    elById("groups-list").classList.toggle("hide");
    elById("groups-list").classList.toggle("show");
});

elById("settings-button").addEventListener("click", () => { 
    elById("settings-list").classList.toggle("hide");
    elById("settings-list").classList.toggle("show");
});


updateData();

window.setInterval(periodicUpdates, 500);


