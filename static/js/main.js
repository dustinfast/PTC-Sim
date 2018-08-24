var selected_loco = '';

// Sets selected_loco, updates loco table border, and refreshes status map
var old_border;
function home_loco_select(locoID) {
    if (selected_loco != '') {
        document.getElementById(selected_loco).style.border = old_border;
    }
    old_border = document.getElementById(locoID).style.border;

    if (selected_loco == locoID) {
        selected_loco = '';
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

            // Clear markers from existing map
            for (var i = 0; i < panel_map_markers.length; i++) {
                panel_map_markers[i].setMap(null);
            }
            panel_map_markers = []

            // Add new markers to map
            $.each(data.status_map.markers, function (i) {
                var marker = new google.maps.Marker({
                    position: new google.maps.LatLng(
                        data.status_map.markers[i].lat, 
                        data.status_map.markers[i].lng
                    ),
                    icon: data.status_map.markers[i].icon,
                    map: panel_map,
                });
                panel_map_markers.push(marker);
            });

            // TODO: recenter map
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
    }, 60000);
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


