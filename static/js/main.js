// Home Content Updater
function get_home_locotable_async() {
    $.getJSON($SCRIPT_ROOT + "/_home_locotable_update",
        function (data) {
            $("#locos_table").html(data.locos_table);
        });
    }

function get_home_map_async() {
    $.getJSON($SCRIPT_ROOT + "/_home_map_update",
        function (data) {
            panel_map_markers.map(function (mk) { mk.setMap(panel_map) });
        });
}

function update_home_content_async() {
    get_home_locotable_async();
    get_home_map_async();
    setInterval(function () {
        get_home_locotable_async();  
        get_home_map_async();
    }, 5000);
}
// End Home Content Updater

// Loco table -> Select Loco Handler

// End Loco table -> Select Loco Handler


