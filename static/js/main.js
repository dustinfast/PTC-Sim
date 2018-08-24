// State vars
var selected_loco = null;
var old_border = null;
var open_infobox = null;
var open_infobox_marker = null;

// Sets selected_loco, updates loco table border, and refreshes status map
function home_loco_select(locoID) {
    if (selected_loco) {
        document.getElementById(selected_loco).style.border = old_border;
    }
    old_border = document.getElementById(locoID).style.border;

    if (selected_loco == locoID) {
        selected_loco = null;
    } else {
        selected_loco = locoID;
        document.getElementById(selected_loco).style.border = "thick solid";
    }
    
    console.log('Selected loco: ' + selected_loco);
    home_get_map_async();
}

// Updates home.locos_table 
function home_get_locotable_async() {
    $.getJSON(
        $SCRIPT_ROOT + '/_home_get_locotable',
        function (data) {
            $('#locos_table').html(data.locos_table);
        });
    }
    
// Requests a status map for the loco specified by selected_loco.
// If selected_loco = '', requests a generic status map with all locos.
function home_get_map_async() {
    $.ajax({
        url: $SCRIPT_ROOT + '/_home_get_statusmap',
        type: 'POST',
        contentType: 'application/json;charset=UTF-8',
        data: JSON.stringify({ 'locoID': selected_loco }),

        success: function (data) {
            if (data == 'error') {
                console.error('Error returned fetching status map.')
                return;
            }

            // Remove existing map markers
            panel_map_markers.forEach(function (marker) {
                    marker.setMap(null);
                });
            panel_map_markers = []

            // Add new markers to map
            $.each(data.status_map.markers, function (i) {
                var infowindow = new google.maps.InfoWindow({
                    content: data.status_map.markers[i].infobox
                });
                google.maps.event.addListener(infowindow, 'closeclick', function () {
                    open_infobox_marker = null;  // infowindow closed
                });
                var marker = new google.maps.Marker({
                    position: new google.maps.LatLng(
                        data.status_map.markers[i].lat,
                        data.status_map.markers[i].lng
                    ),
                    icon: data.status_map.markers[i].icon,
                    title: i.toString(), // TODO: Not going to be unqiue
                    map: panel_map
                });
                marker.addListener('click', function () {
                    infowindow.open(panel_map, marker);
                    open_infobox_marker = marker;  // infowindow opened
                });
                panel_map_markers.push(marker);
                
                // Open the infobox for this marker, if it was previously open
                if (open_infobox_marker && open_infobox_marker.title == marker.title) {
                    infowindow.open(panel_map, marker);
                }

            });


            // TODO: recenter map. panel_map.center?
            console.log('success');
        }
    });
}

// Updates the home page locos table and panel map at the given interval
function home_update_content_async() {
    home_get_locotable_async();
    home_get_map_async();
    setInterval(function () {
        home_get_locotable_async();
        home_get_map_async();
    }, 5000);
}

// Working AJAX GET
// function home_get_map_async() {
//     $.getJSON($SCRIPT_ROOT + '/_home_map_update',
//         function (data) {
//             console.log(data.status_map.markers)
//             });
//         });
// }

// Working AJAX POST
// function home_loco_select(locoID) {
//     $.ajax({
//         url: $SCRIPT_ROOT + '/_home_select_loco',
//         type: 'POST',
//         contentType: 'application/json;charset=UTF-8',
//         data: JSON.stringify({ 'locoID': locoID }),
//         success: function () {
//             console.log('success');
//         }
//     });
// }


