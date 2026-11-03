//部门id
 //var deptIdArr = '1750348077562798080,1753257945428434944,1754308577497227264,1753258091356659712,1753974579235430400,1754039426161614848,1753258310437740544,1753258172973621248,1753974449669185536,1753258426598989824,1754039504351830016,1753258452280713216,1753258501366652928,1754039348189503488,1753323894886146048,1753967989497307136,1753258285058007040,1753257897193938944,1754039927125090304,1753257978211115008,1753258369661313024,1753258201813655552,1754039891683221504,1754041065568247808,1753258062764089344,1752890352880361472,1754039768567816192,1753258343505633280,1753967851886387200,1753258477425565696,1754039192358526976,1753258037782814720,1753258230917931008,1753258005776080896,1753258256310247424,'
 var deptIdArr = '1750348077562798080'
 //征集部门渠道id
 var collect_siteIds = "1751807511324454912,1815308879718780928,1815926633446510592,1815302427578994688,1815927125501284352,1753255500391583744,1753255854516670464,1815927199392337920,1780115352481099776,1753255723541139456,1753255916894359552,1753254542949421056,1815926794579087360,1753255295696965632,1753255446821933056,1815927368317931520,1753255671938617344,1753255573955481600,1753255385136304128,1815923457179783168,1815931828322701312,1815927468771512320,1753255622856871936,1753255180382965760,1753255123541757952,1753254993270870016,1753254765847318528,1753254937251745792,1753255988319162368,1753254619659046912,1815292128549408768,1815924190839050240,1815926988561453056,1815926704443494400,1815927288424828928,1753255778981449728";
$(function () {
  // 头部搜索
  $("#header-search-btn").on('click', function () {
    if ($("#header-search-txt").val() == "") {
      alert("请输入关键字");
    } else {
      $("#header-search-form").submit();
    }
  })

  //天气预报
  getWeather();

    // 关怀模式放大125%
    $("#wzaLink").click(function(){
        
    })
})

//天气预报
function getWeather() {
  var imgHead = '/jxsrmzf/pc2024/images/weather/';
  $.ajax({
    url: 'https://wx.weather.cn/weather/fwybCityforecast/cityforecastList',
    type: "POST",
    cache: false,
    crossDomain: true,
    success: function (result) {
      // console.log(result);
      var contentHtml = '';
      if (result.code == 0) {
        var cityArr = result.data;
        for (var i = 0; i < cityArr.length; i++) {
          var cityName = cityArr[i].stationName;
          var dayStr = cityArr[i].weather;
          var nightStr = cityArr[i].weatherNight;
          var dayImg = imgHead + cityArr[i].tupian + '.png';
          var nightImg = imgHead + cityArr[i].tupianNight + '.png';
          var minT = cityArr[i].tempmin;
          var maxT = cityArr[i].tempmax;
          var weaStr = dayStr + '转' + nightStr;
          var tempStr = minT + '℃-' + maxT + '℃';
          var imgHtml = '<img class="weaImg" src="' + dayImg + '" /> - <img class="weaImg" src="' + nightImg +
            '" />';
          if (dayStr == nightStr) {
            weaStr = dayStr;
            imgHtml = '<img class="weaImg" src="' + dayImg + '" />';
          }
          contentHtml += '<li>' + cityName + '：' + weaStr + imgHtml + '<span class="qw">(' +
            tempStr + ')</span></li>';
        }
        var scrollHtml = '<ul id="scroll_begin">' + contentHtml + '</ul><ul id="scroll_end">' + contentHtml +
          '</ul>';
        $('#scroll_div').empty().html(scrollHtml);
        ScrollImgLeft();
      }
    },
    complete: function (XMLHttpRequest, textStatus) {
      this; // 调用本次AJAX请求时传递的options参数
    }

  });
}

//文字横向滚动
function ScrollImgLeft() {
  var speed = 50;
  var MyMar = null;
  var scroll_begin = document.getElementById("scroll_begin");
  var scroll_end = document.getElementById("scroll_end");
  var scroll_div = document.getElementById("scroll_div");
  scroll_end.innerHTML = scroll_begin.innerHTML;

  function Marquee() {
    if (scroll_end.offsetWidth - scroll_div.scrollLeft <= 0)
      scroll_div.scrollLeft -= scroll_begin.offsetWidth;
    else
      scroll_div.scrollLeft++;
  }
  MyMar = setInterval(Marquee, speed);
  scroll_div.onmouseover = function () {
    clearInterval(MyMar);
  }
  scroll_div.onmouseout = function () {
    MyMar = setInterval(Marquee, speed);
  }
}



//判断是否是pc端 true为pc端 false为移动端
function IsPC() {
  var userAgentInfo = navigator.userAgent;
  var Agents = new Array("Android", "iPhone", "SymbianOS", "Windows Phone", "iPad", "iPod");
  var flag = true;
  for (var v = 0; v < Agents.length; v++) {
    if (userAgentInfo.indexOf(Agents[v]) > 0) {
      flag = false;
      break;
    }
  }
  return flag;
}