// Updates home.locos_table 
function get_home_locotable_async() {
    $.getJSON($SCRIPT_ROOT + '/_home_locotable_update',
        function (data) {
            $('#locos_table').html(data.locos_table);
        });
        // TODO: Success functions
    }
    
// Updates home.panel_map
function get_home_map_async() {
    $.getJSON($SCRIPT_ROOT + '/_home_map_update',
        function (data) {
            panel_map_markers = []
            panel_map_markers.map(function (mk) { mk.setMap(null) });
            // console.log(data.status_map.markers) // debug
            $.each(data.status_map.markers, function (i) {
                createMarker(data);

                function createMarker(data) {
                    var infowindow = new google.maps.InfoWindow();
                    var marker = new google.maps.Marker({
                        position: new google.maps.LatLng(data.status_map.markers[i].lat, data.status_map.markers[i].lng),
                        icon: data.status_map.markers[i].icon,
                        map: panel_map,
                    });
                    // infowindow.close();
                    // infowindow.setContent(data.status_map.markers[i].infobox);
                    // infowindow.open(panel_map, marker);

                    // google.maps.event.addListener(marker, 'click', function (target, elem) {
                    //     infowindow.open(map, marker);
                    //     $.ajax({
                    //         success: function () {
                    //             infowindow.setContent(contentString);
                    //         }
                    //     });
                };
            });
        });
}

// Updates the home locos table and panel map at the given interval
function home_update_content_async() {
    get_home_locotable_async();
    get_home_map_async();
    setInterval(function () {
        get_home_locotable_async();  
        get_home_map_async();
    }, 60000);
}

// Passes the given locoID back to the server and, on success, reloads map
function home_loco_select(locoID) {
    $.ajax({
        url: $SCRIPT_ROOT + '/_home_select_loco',
        type: 'POST',
        contentType: 'application/json;charset=UTF-8',
        data: JSON.stringify({ 'locoID': locoID }),

        success: function () {
            // get_home_map_async();
            console.log('success');
            // TODO: Highlight loco inner table
        }
    });
}


