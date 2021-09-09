var connect_color = "#294159"
var cut_color = "#895061"
var initial_color = "gray"
var player_role = null
var player_to_move = "connect"
var nodes_data = []
var links_data = []
var board_number = null
var description = {
                   "0": "You have won 10 games in total",
                   "1": "You have won 50 games in total",
                   "2": "You have won 100 games in total",
                   "3": "You have won 5 games in a row, without loosing a single one",
                   "4": "You have won 10 games in a row, without loosing a single one",
                   "5": "You have won 50 games in a row, without loosing a single one",
                   "6": "You have played 50 games in total",
                   "7": "You have played 100 games in total",
                   "8": "You have played 500 games in total",
                   }
const csrftoken = getCookie('csrftoken');

$.ajax({
    type: "GET",
    url: "/loadGraph/",
    cache: false,
    headers: {'X-CSRFToken': csrftoken},
    success: function (data, textStatus, jqXHR) {
        var raw_data = JSON.parse(data)
        nodes_data = raw_data["nodes"]
        links_data = raw_data["edges"]
        player_role = raw_data["role"]
        board_number = raw_data["board_number"]
    },
    error: function (XMLHttpRequest, textStatus, errorThrown) {
        alert("some error");
    },
    async: false
});

const chatSocket = new WebSocket(
    'ws://'
    + window.location.host
    + '/ws/chat/'
    + board_number
    + '/'
);

chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    if (data.message.hasOwnProperty("achievements")){
        data.message["achievements"][player_role].forEach(element => {
                toastr.info(description[element], 'New achievement')
        });
    }
        if (data.message.source != null){
            d3.selectAll("line")._groups[0].forEach(element => {
                if (element.__data__.source.number==data.message.source && element.__data__.target.number==data.message.target){
                    if (data.message.player == "cut"){
                        d3.select(element).style("stroke", cut_color)
                        player_to_move = "connect"
                    }
                    else{
                        player_to_move = "cut"
                        d3.select(element).style("stroke", connect_color)
                    }

                }
            })
        }

//    console.log(d3.selectAll("line")._groups[0].filter(function() {
//    return d3.select(this).attr("__data__").index == 0; // filter by single attribute
//  }))

//    document.querySelector('#chat-log').value += (data.message + '\n');

    if (data.message.game_finished === true){
        if (player_role === "connect" && data.message.connect_won === true){
            $("#endgame_header").text('You Won')
        }
        if (player_role === "cut" && data.message.cut_won === true){
            $("#endgame_header").text('You Won')
        }
        $("#endgame_message").text(data.message.message)

        $("#endgame_form").addClass("active");
    }
};

chatSocket.onclose = function(e) {
    console.error('Game socket closed unexpectedly');
};

var svg = d3.select("svg"),
//    width = +svg.attr("width"),
//    height = +svg.attr("height");



//TODO FIX TIS IF POSSIBLE. width abd height should be dynamically set

    width = 800
    height = 800


var radius = 5;


//set up the simulation and add forces
var simulation = d3.forceSimulation()
    .nodes(nodes_data);

var link_force = d3.forceLink(links_data)
    .id(function (d) {
        return d.number;
    });

var charge_force = d3.forceManyBody()
    .strength(-500);

var center_force = d3.forceCenter(width / 2, height / 2);

simulation
    .force("charge_force", charge_force)
    .force("center_force", center_force)
    .force("links", link_force)
;


//add tick instructions:
simulation.on("tick", tickActions);

//add encompassing group for the zoom
var g = svg.append("g")
    .attr("class", "everything");

//draw lines for the links
var link = g.append("g")
    .attr("class", "links")
    .selectAll("line")
    .data(links_data)
    .enter().append("line")
    .attr("stroke-width", 10)
    .style("stroke", linkColour);

//draw circles for the nodes
var node = g.append("g")
    .attr("class", "nodes")
    .selectAll("circle")
    .data(nodes_data)
    .enter()
    .append("circle")
    .attr("r", radius)
    .attr("fill", circleColour);

//add zoom capabilities
var zoom_handler = d3.zoom()
    .on("zoom", zoom_actions);

zoom_handler(svg);

/** Functions **/

//Function to choose what color circle we have
//Let's return blue for males and red for females
function circleColour(d) {
     if(d.type ==="NODE"){
//     	return "#753d54";
        return "gray";

     } else {
     	return "#c41f6e";
     }

}

//Function to choose the line colour and thickness
//If the link type is "A" return green
//If the link type is "E" return red
function linkColour(d) {
    if (d.state === "initial") {
        return initial_color;
    }
    if (d.state === "cut") {
        return cut_color;
    } else {
        return connect_color;
    }
}

//Zoom functions
function zoom_actions() {
    g.attr("transform", d3.event.transform)
}

function tickActions() {
    //update circle positions each tick of the simulation
    node
        .attr("cx", function (d) {
            return d.x;
        })
        .attr("cy", function (d) {
            return d.y;
        });

    //update link positions
    link
        .attr("x1", function (d) {
            return d.source.x;
        })
        .attr("y1", function (d) {
            return d.source.y;
        })
        .attr("x2", function (d) {
            return d.target.x;
        })
        .attr("y2", function (d) {
            return d.target.y;
        });
}

//  console.log(d3.selectAll("line"))
//
// function sleepFor( sleepDuration ){
//   var now = new Date().getTime();
//   while(new Date().getTime() < now + sleepDuration){ /* do nothing */ }
// }
//
// $( document ).ready(function() {
//    console.log($("#djura"))
// });
//
// $("#djura").click(function () {
//         alert("aerg");
//
//             console.log(d3.selectAll("line"))
//
//     });

// svg.on("click", function() {
//     alert()
// })
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function moveValid(msg) {
    console.log("valid move: " + msg)
}

function moveInvalid(msg) {
    console.log("invalid move: " + msg)
}

d3.selectAll("line").on("click", function () {
    if (player_role == player_to_move){
        if (this.__data__.state === "initial") {
            // console.log(this.__data__.state)
            const that = this;

            chatSocket.send(JSON.stringify({
                    "link": {
                        "source": this.__data__.source.number,
                        "target": this.__data__.target.number
                    }
                }));

    //        $.ajax({
    //            type: "POST",
    //            url: "/move/",
    //            cache: false,
    //            headers: {'X-CSRFToken': csrftoken},
    //            data: JSON.stringify({
    //                "link": {
    //                    "source": this.__data__.source.number,
    //                    "target": this.__data__.target.number
    //                }
    //            }),
    //            success: function (msg) {
    //                moveValid(msg)
    //                console.log("valid")
    //                if (player_role === "connect")
    //                    d3.select(that).style("stroke", connect_color)
    //                else if (player_role === "cut")
    //                    d3.select(that).style("stroke", cut_color)
    //                // alert("Data Saved: " + msg);
    //            },
    //            error: function (msg) {
    //                console.log("invalid")
    //                moveInvalid(msg)
    //                // alert("some error");
    //            }
    //        });
        }
    }
})


function handleMouseOver(d, i) {
    alert("dfg")
}

$(document).ready(function(){

    toastr.options = {
            'closeButton': true,
            'debug': false,
            'newestOnTop': false,
            'progressBar': true,
            'positionClass': 'toast-bottom-right',
            'preventDuplicates': false,
            'showDuration': '2000',
            'hideDuration': '1000',
            'timeOut': '10000',
            'extendedTimeOut': '2000',
            'showEasing': 'swing',
            'hideEasing': 'linear',
            'showMethod': 'fadeIn',
            'hideMethod': 'fadeOut',
        }


    $("#resign_btn").click(function(){
        $("#resign_form").addClass("active");
     });

    $(".modal_close").click(function(){
        $("#resign_form").removeClass("active");
        $("#endgame_form").removeClass("active");
    });

    $("#endgame_ok_btn").click(function(){
        $("#endgame_form").removeClass("active");
    });

    $("#resign_cancel_btn").click(function(){
        $("#resign_form").removeClass("active");
    });

    $("#resign_confirm_btn").click(function(){
        $("#resign_form").removeClass("active");
        chatSocket.send(JSON.stringify({
            "link": {
                "source": "",
                "target": ""
            },
            "resigned":true
        }));
    });
});
