const csrftoken = getCookie('csrftoken');

var photos = null
$.ajax({
    type: "GET",
    url: "/boards/",
    cache: false,
    headers: {'X-CSRFToken': csrftoken},
    success: function (data, textStatus, jqXHR) {
        photos = JSON.parse(data)
    },
    error: function (XMLHttpRequest, textStatus, errorThrown) {
        alert("some error");
    },
    async: false
});

let gallery = document.querySelector('.gallery');

const preloader_colors = [
    'rgb(231, 216, 75)',
    'rgb(214, 28, 89)',
    'rgb(54, 7, 69)',
    'rgb(27, 135, 152)',
    'rgb(239, 234, 197)',
    'rgb(54, 7, 69)',
    'rgb(239, 234, 197)',
    'rgb(231, 216, 75)',
    'rgb(214, 28, 89)'
]

function build_gallery() {
    for (let i = 0; i < photos.length; i++) {
        gallery.innerHTML += `<div class="loader">
                                <img class="thumb"/>
                                <div class="preloader"></div>
                              </div>`
    }

    const loader = document.querySelectorAll('.loader');
    const preloader = document.querySelectorAll('.preloader');
    const thumb = document.querySelectorAll('.thumb');

    for (let i = 0; i < preloader.length; i++) {

        for (let y = 0; y < preloader_colors.length; y++) {
            let div = document.createElement('div');
            div.style.backgroundColor = preloader_colors[y];
            div.className = `square`;
            preloader[i].appendChild(div);
        }

        let square = preloader[i].querySelectorAll(`.square`);
        let preloaderCol = preloader_colors.concat();
        preloader[i].update = setInterval(()=>{
            const newArray = changeColor(preloaderCol);
            square.forEach((sq, z) => sq.style.backgroundColor = newArray[z]);

        },50);

        preloader[i].stopPreloader = function stopPreloader(){
        preloader[i].style.opacity = 0;
        clearInterval(preloader[i].update);
        thumb[i].style.opacity = 1;
        }

        thumb[i].addEventListener('load', preloader[i].stopPreloader);
    }

    for (let i = 0; i < thumb.length; i++) {
        thumb[i].src = photos[i]["url"];
        loader[i].addEventListener("click", function(){imageClick(photos[i]["alias"]);});
    }


    /*
    // loop over the photos urls
    // create the following structure for every url
    // add it to the gallery container
    // each photo url is loaded to the <img> tag
    // each 'preloader' should contain the preloader animation we did in the previous stages */
}

function changeColor(arr) {
    let lastColor = arr.pop();
    arr.unshift(lastColor);
    return arr;
}

window.addEventListener("DOMContentLoaded", build_gallery);

function imageClick(alias){
    console.log(window.location.href + "game.html?alias=" + alias);
//    window.location.href = window.location.href + "game?alias=" + alias
    window.location.href = window.location.href + "game.html/" + alias
}

//**********************************************************************************************************************
//*********************************************LEADERBOARD**************************************************************
//**********************************************************************************************************************

(function ($) {
	var FakePoller = function(options, callback, url){
	    this.url = url
		var defaults = {
			frequency: 60,
			limit: 10
		};
		this.callback = callback;
		this.config = $.extend(defaults, options);
//		this.list = [
//			'Game of Thrones',
//			'The Walking Dead',
//			'Survivor',
//			'Dead Like Me',
//			'Being Human',
//			'American Idol',
//			'X Factor',
//			'Firefly',
//			'SGU',
//			'Battlestar Galactica',
//			'Farscape',
//			'The Mentalist',
//			'True Blood',
//			'Dexter',
//			'Rick Astley',
//			'Jaje koko Django'
//		];
        this.list = []
        $.ajax({
            type: "GET",
            url: this.url,
            cache: false,
            headers: {'X-CSRFToken': csrftoken},
            success: function (data, textStatus, jqXHR) {
                parsedData = JSON.parse(data)
                leaderboard_entries = parsedData
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("some error");
            },
            async: false
        });
        this.list = Object.keys(leaderboard_entries)
        this.values = Object.values(leaderboard_entries)

	}
	FakePoller.prototype.getData = function() {
        $.ajax({
                type: "GET",
                url: this.url,
                cache: false,
                headers: {'X-CSRFToken': csrftoken},
                success: function (data, textStatus, jqXHR) {
                    parsedData = JSON.parse(data)
                    leaderboard_entries = parsedData
                },
                error: function (XMLHttpRequest, textStatus, errorThrown) {
                    alert("some error");
                },
                async: false
            });
        this.list = Object.keys(leaderboard_entries)
        this.values = Object.values(leaderboard_entries)
		var results = [];
		for (var i = 0, len = this.list.length; i < len; i++) {
			results.push({
				name: this.list[i],
				count: this.values[i]
			});
		}
		return results;
	};
	FakePoller.prototype.processData = function() {
		return this.sortData(this.getData()).slice(0, this.config.limit);
	};

	FakePoller.prototype.sortData = function(data) {
		return data.sort(function(a, b) {
			return b.count - a.count;
		});
	};
	FakePoller.prototype.start = function() {
		var _this = this;
		this.interval = setInterval((function() {
			_this.callback(_this.processData());
		}), this.config.frequency * 1000);
		this.callback(this.processData());
		return this;
	};
	FakePoller.prototype.stop = function() {
		clearInterval(this.interval);
		return this;
	};
	window.FakePoller = FakePoller;

	var Leaderboard = function (elemId, options, url) {
		var _this = this;
		var defaults = {
			limit:10,
			frequency:15
		};
		this.currentItem = 0;
		this.currentCount = 0;
		this.config = $.extend(defaults,options);

		this.$elem = $(elemId);
		if (!this.$elem.length)
			this.$elem = $('<div>').appendTo($('body'));

		this.list = [];
		this.$content = $('<ul>');
		this.$elem.append(this.$content);

		this.poller = new FakePoller({frequency: this.config.frequency, limit: this.config.limit}, function (data) {
			if (data) {
				if(_this.currentCount != data.length){
					_this.buildElements(_this.$content,data.length);
				}
				_this.currentCount = data.length;
				_this.data = data;
				_this.list[0].$item.addClass('animate');
			}
		}, url);

		this.poller.start();
	};

	Leaderboard.prototype.buildElements = function($ul,elemSize){
		var _this = this;
		$ul.empty();
		this.list = [];

		for (var i = 0; i < elemSize; i++) {

			var item = $('<li>')
				.on("animationend webkitAnimationEnd oAnimationEnd",eventAnimationEnd.bind(this, i+1) )
				.appendTo($ul);

            if(i === 0) {
                this.list.push({
                   $item: item,
                   $name: $('<img src="/static/images/gold-medal.png" class="medal" /><span class="name">Loading...</span>').appendTo(item),
                   $count: $('<span class="count">Loading...</span>').appendTo(item)
               });
            } else {
                if(i === 1) {
                this.list.push({
                   $item: item,
                   $name: $('<img src="/static/images/silver.png"  class="medal" /><span class="name">Loading...</span>').appendTo(item),
                   $count: $('<span class="count">Loading...</span>').appendTo(item)
               });
            } else {
                if(i === 2) {
                    this.list.push({
                   $item: item,
                   $name: $('<img src="/static/images/medal.png"  class="medal" /><span class="name">Loading...</span>').appendTo(item),
                   $count: $('<span class="count">Loading...</span>').appendTo(item)
               });
                } else {
                    this.list.push({
                       $item: item,
                       $name: $('<span class="name">Loading...</span>').appendTo(item),
                       $count: $('<span class="count">Loading...</span>').appendTo(item)
                   });}
            }
            }


		}

		function eventAnimationEnd (index, evt){
            if(index > 3)
			    this.list[this.currentItem].$name.text(index + '.\xa0\xa0\xa0' + _this.data[this.currentItem].name);
			else this.list[this.currentItem].$name.text(_this.data[this.currentItem].name);
			this.list[this.currentItem].$count.text(_this.data[this.currentItem].count);
			this.list[this.currentItem].$item.removeClass('animate');
			this.currentItem = this.currentItem >= this.currentCount - 1 ? 0 : this.currentItem + 1;
			if (this.currentItem != 0) {
				this.list[this.currentItem].$item.addClass('animate');
			}
		}
	};

	Function.prototype.bind = function(){
		var fn = this, args = Array.prototype.slice.call(arguments),
			object = args.shift();
		return function(){
			return fn.apply(object,args.concat(Array.prototype.slice.call(arguments)));
		};
	};

	window.Leaderboard = Leaderboard;
	//Helper
	function rnd (min,max){
		min = min || 100;
		if (!max){
			max = min;
			min = 1;
		}
		return	Math.floor(Math.random() * (max-min+1) + min);
	}

	function numberFormat(num) {
		return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
	}
})(jQuery);

$(document).ready(function ($) {
	var myLeaderboardRatings = new Leaderboard("#users_ratings", {limit:10,frequency:8}, "/usersRatings/");
    var myLeaderboardMostWins = new Leaderboard("#users_wins", {limit:10,frequency:8}, "/usersWins/");
    var myLeaderboardMostWins = new Leaderboard("#users_achievements", {limit:10,frequency:8}, "/usersAchievements/");
    var myLeaderboardLogins = new Leaderboard("#users_max_logins", {limit:10,frequency:8}, "/usersMaxLogins/");

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
});



//**********************************************************************************************************************
//*********************************************LEADERBOARD**************************************************************
//**********************************************************************************************************************


var description = {"12": "You have logged in 7 days in a row",
                   "13": "You have logged in 14 days in a row",
                   "14": "You have logged in 31 days in a row"}

$.ajax({
    type: "GET",
    url: "/newAchievement/",
    cache: false,
    headers: {'X-CSRFToken': csrftoken},
    success: function (data, textStatus, jqXHR) {
        dict_data = JSON.parse(data)
        console.log(dict_data)
        if (dict_data["achievement"] != -1){
            toastr.info(description[dict_data["achievement"]], 'New achievement')
        }
    },
    error: function (XMLHttpRequest, textStatus, errorThrown) {
        alert("some error");
    },
    async: true
});



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