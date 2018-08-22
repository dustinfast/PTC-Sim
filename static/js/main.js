// Queries the server for updated home content json
function test() {
    $.getJSON($SCRIPT_ROOT + "/_home_update",
        function (data) {
            $("#locos_table").html(data.locos_table);
            // $("#main_panel").html(data.main_panel);
            // alert(data.locos_table);
        });
    }

function get_home_content_async() {
    test();
    setInterval(function () {
        test();  
    }, 2000);
}
