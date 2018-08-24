// Home Content Updater
function get_home_locotable_async() {
    $.getJSON($SCRIPT_ROOT + "/_home_locotable_update",
        function (data) {
            $("#locos_table").html(data.locos_table);
        });
        // TODO: Success functions
    }

    
function get_home_map_async() {
    $.getJSON($SCRIPT_ROOT + "/_home_map_update",
        function (data) {
            panel_map_markers = []
            panel_map_markers.map(function (mk) { mk.setMap(null) });
            // console.log(data.status_map.markers)
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

function update_home_content_async() {
    get_home_locotable_async();
    get_home_map_async();
    setInterval(function () {
        get_home_locotable_async();  
        get_home_map_async();
    }, 60000);
}
// End Home Content Updater

// Loco table -> Select Loco Handler

// End Loco table -> Select Loco Handler


