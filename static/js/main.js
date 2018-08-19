// Queries the server for updated home content json
function home_content_updater() {
    setInterval(function () {
        $.getJSON($SCRIPT_ROOT + "/_home_update",
            function (data) {
                $("#locos_table").html(data.locos_table);
                $("#main_panel").html(data.main_panel);
                // alert(data.locos_table);
            });
    }, 2000);
}

// function loco_selected() {
