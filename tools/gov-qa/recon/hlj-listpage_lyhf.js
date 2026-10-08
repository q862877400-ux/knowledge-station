'use strict';

var cName = '';
var code = $('meta[name=code]').attr('content');
var channelId = $('meta[name=channelId]').attr('content');
var ispiclist = $('.piclist').length > 0;

(function () {

	var listLi = $('#list li'),
	    num = parseInt($("#pageSize").val());
	if (listLi.length < num + 1) {
		$('.columnMore').hide();
	} else {
		listLi.eq(num).hide();
		$('.columnMore').click(function () {
			$(this).hide();
			$("#page_div").bindEvent({});
			table_ajax();
		});
	}
	// 图片损坏替换默认图片
	$(".piclist img.img").each(function(){
		var _src = $(this).attr('src');
		if(_src == '' || _src == '/null'){
			$(this).attr('src','/hlj/xhtml/images/zwgk/tb_default.png'); //替换损坏的图片
		}
	})
})();

function GetQueryString(name) {
	var reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)');
	var r = window.location.search.substr(1).match(reg);
	if (r != null) return decodeURI(r[2]);
	return null;
}

function table_page(totalHits) {
	var totalHits = parseInt(totalHits);
        console.log(totalHits);
	var pageSize = parseInt($("#pageSize").val());
	var page = parseInt($("#page").val());
	var pageNum = Math.floor((totalHits + pageSize - 1) / pageSize);

	var options = {
		pageNum: pageNum,
		current: page,
		backfun: function backfun(e) {
			$("#page").val(e.current);
			table_ajax();
		}
	};

	$("#page_div").createPage(options);
}

function table_ajax() {
	$.ajax({
		url: '/common/search/' + channelId + '?_isAgg=false&_isJson=true&_pageSize=' + parseInt($("#pageSize").val()) + '&_template=index&_rangeTimeGte=&_channelName=&page=' + parseInt($("#page").val()) + '',
		type: 'get',
		async: false,
		success: function success(data) {

			table_page(data.data.total);
			table_each("list", ajax_success(data));
		},
		error: function error(err) {
			console.log(err);
		}
	});
}

function ajax_success(json) {
	var list = [];
	var resutList = json.data.results;
	$.each(resutList, function (name, val) {
		var myValues = val;
		var json = {
			"title": myValues.title,
			"url": myValues.url,
			"publishedTimeStr": val.publishedTimeStr
		};
		if (ispiclist) {
			json.imgsrc = val.resList.length > 0 ? val.resList[0].filePath : '';
		}
		list.push(json);
	});
	return list;
}

function table_each(id, json) {
	var tab = $("#" + id);
	tab.empty();
	var _li = '';
	$.each(json, function (k, v) {
		if (ispiclist) {
			_li += '<li class="imgscale"><a href="' + v.url + '" class="" target="_blank"> <p><img class="img" src="' + v.imgsrc + '" alt=""></p> <span>' + v.title + '</span> </a></li>';
		} else {
			_li += '<li>\
						<div class="lititle"><h3><a href="' + v.url + '" target="_blank">' + v.title + '</a></h3>\
						<font>' + v.domainMetaList.0 + '</font>\
						<a class="btn">' + v.domainMetaList[0].resultList[10].value + '</a>\
						<a class="' + (v.domainMetaList[0].resultList[3].value ? "btn" : "btnhide") + '">' + (v.domainMetaList[0].resultList[3].value ? v.domainMetaList[0].resultList[3].value : " ") + '</a>\
						<span><b>回复时间： </b>' + v.domainMetaList[0].resultList[4].value.substr(0, 10) + '</span></div>\
						</li>';
		}
	});
	tab.html(_li);

}
function requestParent() {
	$.ajax({
		url: '/common/getLocalList?regionCode=' + code + '',
		//url: '/common/getLocalList?regionCode=' + GetQueryString('code'),
		type: 'get',
		async: 'true',
		success: function success(data) {
			var _nav = '';
			if (data.code == '200') {
				_nav = '<p><a href="/gsszf/index.shtml">首页</a> > ';
				for (var i = 0; i < data.results.channelLevel.length; i++) {
					if (i != data.results.channelLevel.length - 1) {
						_nav += '<a href="' + data.results.channelLevel[i].url + '">' + data.results.channelLevel[i].channelName + '</a> > ';
					} else {
						_nav += '<span>' + data.results.channelLevel[i].channelName + '</span>';
					}
				}
				_nav += '</p>';
			}
			//$('#BreadcrumbNav').empty().html( _nav);
			var a = $('.BreadcrumbNav a').eq(1).html().trim();
			$(".nav a").each(function () {
				if ($(this).text() == a) {
					$(this).addClass("active").siblings().removeClass('active');
				}
			});
		},
		error: function error(err) {
			console.log(err);
		}
	});
}