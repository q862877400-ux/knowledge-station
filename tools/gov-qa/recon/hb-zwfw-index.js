// 全局申明事项跳转数据searchSelectData
var searchSelectData = {
  transactNameBase64: "",
  regionCode: "",
  areaGrade: "",
  regionName: "",
};
$(function () {
  $('#footer').load('/common/layout/footer/xysFooter.html'); //引入页面底部
  $('#sideEdge').load('/common/layout/toolbar/xysToolbar.html'); //引入页面侧边栏
  // $('#selectRegionTheme').load('/common/layout/selectRegion/searchSelectRegionTheme.html?v=20210412') // 引入主题集成服务的区划选择弹窗
  // 个人、法人服务区划弹框
  $('#selectRegion').load('/common/layout/selectRegion/searchSelectRegionGrFr.html') // 引入搜索页的区划选择弹窗
  // 一事联办·主题集成服务 引用一业一证弹框  2023.2.21 df
  // $('#selectRegionYyyz').load('/webview/yyyz/searchSelectRegion.html?v=20230221') // 引入一业一证的区划选择弹窗
  $("#wza").load("/x_wza/index.html", function () {
    // var bfOpenFlag = localStorage.getItem('bf') || "off"
    // if (bfOpenFlag == 'on') {
    //   setTimeout(function () {
    //     $('#wza').show()
    //     $('#bf_body').addClass('open')
    //     $('#bf_box').show()
    //     getReadToken()
    //     doFont(document.body)
    //   }, 3000);
    // }
    // $("#bf-assist-exit").click();
    // 读屏功能
    getdictionary('YSLB_SMZQ_GR')
    getdictionary('YSLB_SMZQ_FR');
    try {
      $.splitArea({
        pageInfo: {
          type: "综合页"
        },
        nav: [{
          el: ".andy-nav", //配置导航区的类名
          desc: "主栏目导航", //导航区的名称
        },],
        window: [{
          el: ".newTszq", //配置视窗区的类名
          desc: "特色专区", //视窗区的名称
        },
        {
          el: ".newGrFrModel", //配置视窗区的类名
          desc: "个人服务、法人服务、部门服务", //视窗区的名称
        },
        {
          el: ".newGrFr_bottom", //配置视窗区的类名
          desc: "便民服务", //视窗区的名称
        },
        {
          el: ".top_yslb_x", //配置视窗区的类名
          desc: "一事联办·主题集成服务", //视窗区的名称
        },
        {
          el: ".top_zt_x", //配置视窗区的类名
          desc: "优化营商环境", //视窗区的名称
        },
        {
          el: ".zwgkCont", //配置视窗区的类名
          desc: "政务公开", //视窗区的名称
        },
        {
          el: ".zwfwhcp-wrap", //配置视窗区的类名
          desc: "政务服务好差评", //视窗区的名称
        },
        {
          el: ".footer", //配置视窗区的类名
          desc: "底部功能区", //视窗区的名称
        },
        ],
        interactive: [{
          el: ".andy-main-search", //配置交互去的类名
          desc: "搜索区", //交互区的名称
        },],
      });
      $.elderOptions([{
        el: ".andy-nav", //配置导航区的类名
        desc: "主栏目导航", //导航区的名称
      },
      {
        el: ".newTszq", //配置视窗区的类名
        desc: "特色专区", //视窗区的名称
      },
      {
        el: ".newGrFrModel", //配置视窗区的类名
        desc: "个人服务、法人服务、部门服务", //视窗区的名称
      },
      {
        el: ".newGrFr_bottom", //配置视窗区的类名
        desc: "便民服务", //视窗区的名称
      },
      {
        el: ".top_yslb_x", //配置视窗区的类名
        desc: "一事联办·主题集成服务", //视窗区的名称
      },
      {
        el: ".top_zt_x", //配置视窗区的类名
        desc: "优化营商环境", //视窗区的名称
      },
      {
        el: ".zwgkCont", //配置视窗区的类名
        desc: "政务公开", //视窗区的名称
      },
      {
        el: ".zwfwhcp-wrap", //配置视窗区的类名
        desc: "政务服务好差评", //视窗区的名称
      },
      {
        el: ".andy-main-search", //配置交互去的类名
        desc: "搜索区", //交互区的名称
      },
      ]);
      
    } catch (error) {
      
    }
  }); // 引入无障碍插件



  $('.ss_city_name').text(p_region_name)
  $('.cyfw').show()
  //切换老版本门户网站
  $('#qhlbbmh').click(function () {
    window.open('/index5.jspx');
  })
  //湖北省人民政府
  $('#tzrmzf').click(function () {
    window.open('https://www.hubei.gov.cn/');
  })
  $('#ehb').click(function () {
    window.open('/webview/ehbptjs/index.html');
  })
  //点击导航栏
  $('#andy-nav').on('click', 'li:not(".hlw_jg"):not(".nav_yslb")', function () {
    $(this).addClass('active').siblings().removeClass('active');
  })

  $('.logo').click(function () { //logo
    sessionStorage.setItem("active_nav_item", "nav_index");
    // sessionStorage.setItem("p_region_code", "420000000000");
    // sessionStorage.setItem("p_region_name", "湖北省");
    // sessionStorage.setItem("p_region_grade", "2");
    setSessionRegionCode('420000000000', '湖北省', '2')
    window.location.href = window.location.origin;
  });
  $('.gov_logo').click(function () {
    window.open('https://www.hubei.gov.cn/');
  })
  $('#nav_index').click(function () { //首页
    sessionStorage.setItem("active_nav_item", "nav_index");
    window.location.href = window.location.origin;
  });
  $('#nav_grfw').click(function () { //切换个人服务
    sessionStorage.setItem("active_nav_item", "nav_grfw");
    window.location.href = "/webview/fw/grfw.html?v=20211029";
  })
  $('#nav_frfw').click(function () { //切换法人服务
    sessionStorage.setItem("active_nav_item", "nav_frfw");
    window.location.href = '/webview/fw/frfw.html?v=20211029';
  })
  $('#nav_bmfwNew').click(function () { //切换部门服务
    sessionStorage.setItem("active_nav_item", "nav_bmfwNew");
    window.location.href = '/webview/bszn/bmsyNew.html';
  })
  $('#nav_ywtb').click(function () { //一网通版
    sessionStorage.setItem("active_nav_item", "nav_ywtb");
    window.location.href = '/webview/ywtb/ywtb.html';
  })
  $('#nav_yslb').click(function () { //一事联办
    if (sessionStorage.getItem('p_region_code').substr(0, 4) == '4201') {
      // window.location.href = 'http://fyzq.home.wuhan.gov.cn:8001';
      // window.location.href = 'http://58.48.74.43:18048/home';
      window.location.href = "/shell_pc/oneThingSpecialColumn/provinceTheme/localSpecialThemeList?region=420100000000";
      // window.location.href = "http://zwfw.hubei.gov.cn/shell_pc/oneThingSpecialColumn/localspecialTheme/localspecialThemeList?region=420100000000";
    } else {
      // sessionStorage.setItem("active_nav_item", "nav_yslb");
      window.open('/shell_pc/onethingspecialcolumn/provincetheme');
      // window.location.href = '/shell_pc/onethingspecialcolumn/provincetheme';//'/shell_pc/yslb';
    }
  })
  $('#nav_yyyz').click(function () { //一事联办
    // if (sessionStorage.getItem('p_region_code').substr(0, 4) == '4201') {
    //   // window.location.href = 'http://fyzq.home.wuhan.gov.cn:8001';
    //   // window.location.href = 'http://58.48.74.43:18048/home';
    //   window.location.href = "/webview/yslb/whYslb/yslbWh.html";
    // } else {
    //   sessionStorage.setItem("active_nav_item", "nav_yslb");
    //   window.location.href = '/shell_pc/yslb';
    // }
    // if(window.location.port){
    // 	window.location.href = "/shell_pc/yyyz";
    // }else{
    window.location.href = '/webview/yyyz/index.html';
    // }

  })
  $('#nav_bmfw').click(function () { //便民服务
    sessionStorage.setItem("active_nav_item", "nav_bmfw");
    window.location.href = '/webview/bmfw/bmfw.html';
  })
  $('#nav_zwgk').click(function () { //政务公开
    sessionStorage.setItem("active_nav_item", "nav_zwgk");
    window.location.href = "/webview/zwgk/zwgk.html?v=20211029";
  })
  $('#nav_hcp').click(function () { //好差评
    sessionStorage.setItem("active_nav_item", "nav_hcp");
    window.location.href = '/webview/hcp/hcp.html';
  })
  $('#nav_zmhd').click(function () { //政民互动
    sessionStorage.setItem("active_nav_item", "nav_zmhd");
    window.location.href = "/webview/bszn/zmhd.html?v=20211029";
  })
  $('#nav_yqzq').click(function () { //疫情专区
    if (sessionStorage.getItem('p_region_code').substr(0, 4) == '4201') {
      sessionStorage.setItem("active_nav_item", "nav_yqzq");
      window.location.href = '/webview/whWeb/whyqzq.html';
    } else {
      sessionStorage.setItem("active_nav_item", "nav_yqzq");
      window.location.href = '/webview/yqzq/index.html';
    }
  })



  var qcordFlag = true;
  // 扫码登录
  $('#qcord_login').click(function (e) {
    e.stopPropagation()
    $(".qrCode_wrap").toggle();
    if (qcordFlag) {
      createQrcode()
      qcordFlag = false;
    } else {
      qcordFlag = true;
      socket.close();
    }
    // location.href = 'http://prod-pass4.ehbapp.hubei.gov.cn:8050/static/bm_service5.0/scanCodeLogin/index.html'

  })

  // 鄂汇办登录二维码
  var socket;

  function newGuid() {
    var guid = "";
    for (var i = 1; i <= 32; i++) {
      var n = Math.floor(Math.random() * 16.0).toString(16);
      guid += n;
      if (i == 8 || i == 12 || i == 16 || i == 20) guid += "-";
    }
    return guid;
  }

  function createQrcode() {
    // $("#uuid").val("TYKYLogin" + newGuid());
    $(".qrCode_index > canvas").remove();
    var uuid = "https://prod-pass4.ehbapp.hubei.gov.cn/download/page/download.html?TYKYLogin" + newGuid();
    var content;
    $(".qrCode_index").qrcode({
      render: "canvas",
      width: 124,
      height: 124,
      text: uuid,
      background: "#ffffff",
      foreground: "black",
      src: "/images/indexImg/logo-ico.png"
    });
    socketKeepPool(uuid.split("?")[1].substring(9));
  }

  function socketKeepPool(cid) {
    console.log("cid====" + cid);

    if (typeof WebSocket == "undefined") {
      // console.log("您的浏览器不支持WebSocket");
    } else {
      // console.log("您的浏览器支持WebSocket");
      // "ws://prod-pass4.ehbapp.hubei.gov.cn:8050/hbzwapp/socket/" + cid
      socket = new WebSocket(
        // "ws://hbzwapp-user-prod.ehbapp.hubei.gov.cn:8060/app/user/socket/" + cid
        "wss://hbzw-gateway-prod.ehbapp.hubei.gov.cn:40443/4946c655780042a2ad16777c200135a205eb252ecf4e435aaca5db8de39e56bf/" + cid
      );
      //打开事件
      socket.onopen = function () {
        console.log("Socket 已打开");
      };
      //获得消息事件
      socket.onmessage = function (msg) {
        console.log(msg);
        var data = JSON.parse(msg.data);
        console.log(data)
        if (data.code == "0") {
          socket.close();
          window.location.href = window.atob(data.url);
        }
      };
      //关闭事件
      socket.onclose = function () {
        // console.log("Socket已关闭");
      };
      //发生了错误事件
      socket.onerror = function () {
        // console.log("Socket发生了错误");
      };
    }
  }



  // 定时获取到用户信息 知道获取为止;
  // var timer_x = setInterval(function () {
  //   if (window.user_name2) {
  //     clearInterval(timer_x)
  //     GAJG_ajax()
  //   }
  // }, 500);


  //中国政务服务平台
  $('#zgzwfwpt').click(function () {
    if (window.screenWidth <= 1024) {
      $('.webBox').toggle()
    } else {
      window.open('https://gjzwfw.www.gov.cn/index.html');
    }
  })

  var curQh = p_region_code; //当前的区划 
  var curGrade = '2' //不确定的等级
  var isCurGrade = '2'
  var curText = p_region_name //当前选中的区划名称
  var serviceClass = '1' //个人服务1  法人服务2 一网通办

  //初始化部门的显示与隐藏
  sxQhCode = getSessionStorageData('p_region_code')
  sxQhCj = getSessionStorageData('p_region_grade')
  isBumenShow(getSessionStorageData('p_region_grade'));

  getlatelySearhBox() //初始化最近搜索

  // popularService(8)       //获取热门服务

  // getServiceClass(1)     //获取个人服务 1 

  // popularService();       //获取便民服务
  getTsserviceData(); //获取特色服务

  // var regionGrade2 = getSessionStorageData("p_region_grade");
  // if ("2" == regionGrade2) {
  // 	 loadGrade3RegionList(); //初始化个人服务选择区划
  // }

  getSearchRegion()
  // 搜索框获取当前区划名称
  function getSearchRegion() {
    var searchRegion = sessionStorage.getItem('p_region_name') || '湖北省'
    if (searchRegion == '湖北省') {
      $('.areaSelectDiv > span').text('湖北省')
    } else {
      $('.areaSelectDiv > span').text(searchRegion)
      $('.areaSelectDiv').attr('title', searchRegion)
    }
  }


  // 区划模块显示与隐藏的js 
  $('#regional-box').on('click', 'div', function () {
    try {
      stopPropagationByBrowser();
    } catch (e) {

    }
    $('.cityCode_h').show();
  })
  $("#cityCode_h").click(function () {
    stopPropagationByBrowser();
  });
  $(document).click(function () {
    $("#cityCode_h").hide();
    $('.zz_box').hide()
  });




  //防止网络延迟，造成的多次点击，重复出现区划
  var selectedBoxClickFlag = true;
  
  //点击当前区划列表
  $('#selectedBox_h').on('click', 'a', function () {
    $('#selectedBox_h').empty();
    $('#bumenList_h').empty();
    curQh = $(this).attr('code');
    
    curGrade = $(this).attr('grade');
    console.log(curQh,curGrade,'区划层级')
    if(curGrade==5||curGrade==6){
      sxQhCode = curQh
      sxQhCj = curGrade
    }
    isBumenShow(curGrade);
    curText = $(this).text();
    if (!selectedBoxClickFlag) {
      return;
    }
    queryQhBmData(curQh);
    //var html = '<li title="' + curText + '"><a href="javascript:;" class="qhLClic" grade="' + curGrade + '" code = "' + curQh + '">' + curText + '</a></li>'
    var html = '<li title="' + curText + '"><a href="javascript:;" class="qhLClic" grade="' + curGrade + '" code = "' + curQh + '">' + curText + '</a></li>'
    $('#curSsq_h').append(html);
    styEdit(curGrade)
    // $('#fww_url').html('湖北政务服务网' + curText);
    $("#fww_url").attr("href", updateUrlParamByName("areaId"));
    $("#fww_url").attr("data-code", curQh);
    $("#fww_url").attr("data-name", curText);
    $("#fww_url").attr("data-grade", curGrade);


    var url = location.href;
    if (url.indexOf("?") != -1) {
      url = url.substring(0, url.indexOf("?"));
    }
    url = url + "?p_region_code=" + curQh;
    if (curGrade == 5 || curGrade == 6) {
      //url = "/webview/bszn/index_jd.html?p_region_code="+curQh;
      //url = "/webview/bszn/bmsy.html?p_region_code="+curQh;
    }
  })
  //点击选中的区划组合列表
  $('#curSsq_h').on('click', 'a', function () {
    $('#selectedBox_h').empty();
    $('#bumenList_h').empty();
    curQh = $(this).attr('code');
    curGrade = $(this).attr('grade');
    if(curGrade==5||curGrade==6){
      sxQhCode = curQh
      sxQhCj = curGrade
    }
    isBumenShow(curGrade);
    queryQhBmData(curQh);
    curText = $(this).text();

    //$('#fww_url').html('湖北政务服务网' + curText);
    $("#fww_url").attr("href", updateUrlParamByName("areaId"));
    $("#fww_url").attr("data-code", curQh);
    $("#fww_url").attr("data-name", curText);
    $("#fww_url").attr("data-grade", curGrade);
    $(this).parent().nextAll().remove();
    styEdit(curGrade)

    var url = location.href;
    if (url.indexOf("?") != -1) {
      url = url.substring(0, url.indexOf("?"));
    }
    url = url + "?p_region_code=" + curQh;
    if (curGrade == 5 || curGrade == 6) {
      //url = "/webview/bszn/index_jd.html?p_region_code="+curQh;
      //url = "/webview/bszn/bmsy.html?p_region_code="+curQh;
    }
  });
  //点击跳转区划对应的首页
  $('#fww_url').click(function () {
    var regionCode = $("#fww_url").attr("data-code");
    var regionName = $("#fww_url").attr("data-name");
    var regionGrade = $("#fww_url").attr("data-grade");

    setSessionRegionCode(regionCode, regionName, regionGrade);
    setSessionDeptCode('', '', '请选择区划');

  })
  //点击部门列表
  $('#bumenList_h').on('click', 'a', function () {
    var deptCode = $(this).attr('code');
    // var deptName = $(this).html();
    var deptName = $(this).parent('li').attr('title')
    var deptShortName = $(this).attr('shortName');
    $("#curDept").html(deptShortName);

    setSessionDeptCode(deptCode, deptName, deptShortName);

    var regionCode = $("#fww_url").attr("data-code");
    var regionName = $("#fww_url").attr("data-name");
    var regionGrade = $("#fww_url").attr("data-grade");

    setSessionRegionCode(regionCode, regionName, regionGrade);

    // window.location.href = location.href;
    window.location.href = "/webview/bszn/bmsy.html?department=" + deptCode;

    //window.location.href = '/web/hb/static/bumen.html?department=' +deptCode;
  })
  // 给当前元素添加一个字体颜色 兄弟元素去除颜色
  function styEdit(grade) {
    // if(grade < 3) return
    $('#curSsq_h').find('a').removeClass('areaActiveColor')
    $('#curSsq_h > li').last().children('a').addClass('areaActiveColor')
    // $('#curSsq_h').children().eq(grade-2).children('a').addClass('areaActiveColor').parent().siblings().children('a').removeClass('areaActiveColor')
  }
  //点击搜索
  $('#searchBtn_index').click(function () {
    var userSearchVal = $.trim($('#searchVal_index').val())
    var reg_x = /alert|and|exec|execute|update|count|truncate|declare|sitename|netuser|xp_cmdshell|like\'|insert|create|drop|table|grant|group_concat|column_name|prompt|ID_PAYLOAD|PAYLOAD|confirm|onmouseenter|information_schema\.columns|table_schema|union|where|select|delete|order|by\'|char|declare|\'or|like|onmouseover|eval|function|\(\)|Function|onclick\%|\'\=\'|\'and\'|content\-type|ltrim\(|onclick=|window\[|\/\*\*\/|iframe|document|script|\<script\>|\"|\'|\。\/|ontoggle|\<details/g
    if (reg_x.test(userSearchVal)) {
      userSearchVal = ''
    }

    // 防止xss和sql注入:JS特殊字符过滤正则
    function stripscript(s) {
      var pattern = new RegExp("[%--`~!@#$^&*()=|{}':;',\\[\\].<>/?~！@#￥……&*（）——|{}【】‘；：”“'。，、？]") //格式 RegExp("[在中间定义特殊过滤字符]")
      var rs = "";
      for (var i = 0; i < s.length; i++) {
        rs = rs + s.substr(i, 1).replace(pattern, '');
      }
      return rs;
    }
    function htmlspecialchars(str) {
      str = str.replace(/&/g, '&amp;');
      str = str.replace(/</g, '&lt;');
      str = str.replace(/>/g, '&gt;');
      str = str.replace(/"/g, '&quot;');
      str = str.replace(/'/g, '&#039;');
      return str;
    }
    // userSearchVal = htmlspecialchars(stripscript(userSearchVal))
    console.log(userSearchVal)


    var keywordArr = localStorage.getItem('gzj') != null ? JSON.parse(localStorage.getItem('gzj')) : [];
    keywordArr.unshift(userSearchVal)
    if (keywordArr.length > 5) {
      keywordArr = keywordArr.slice(0, 5)
    }
    if (userSearchVal) {
      localStorage.setItem('gzj', JSON.stringify(keywordArr)) //存储搜索的关键字
    }
    if (userSearchVal) {
      // console.log('有值跳转')
      //跳转搜索页面
      
      var searchUrl = '/webview/bszn/search/search.html?' + 'Keyword=' + userSearchVal + '&p_region_code=' + curQh + '&curText=' + curText
      console.log(searchUrl,'searchUrl')
      window.open(searchUrl)
    } else {
      $('.warm_tibs').show()
      setTimeout(function () {
        $('.warm_tibs').hide()
      }, 3000);
    }
  })
  //回车事件
  $('#searchVal_index').bind('keypress', function (event) {
    if (event.keyCode == "13") {
      var userSearchVal = $.trim($('#searchVal_index').val())
      var reg_x = /alert|and|exec|execute|update|count|truncate|declare|sitename|netuser|xp_cmdshell|like\'|insert|create|drop|table|grant|group_concat|column_name|prompt|ID_PAYLOAD|PAYLOAD|confirm|onmouseenter|information_schema\.columns|table_schema|union|where|select|delete|order|by\'|char|declare|\'or|like|onmouseover|eval|function|\(\)|Function|onclick\%|\'\=\'|\'and\'|content\-type|ltrim\(|onclick=|window\[|\/\*\*\/|iframe|document|script|\<script\>|\"|\'|\。\/|ontoggle|\<details/g
      if (reg_x.test(userSearchVal)) {
        userSearchVal = ''
      }
      var keywordArr = localStorage.getItem('gzj') != null ? JSON.parse(localStorage.getItem('gzj')) : [];
      keywordArr.unshift(userSearchVal)
      if (keywordArr.length > 5) {
        keywordArr = keywordArr.slice(0, 5)
      }
      if (userSearchVal) {
        localStorage.setItem('gzj', JSON.stringify(keywordArr)) //存储搜索的关键字
      }
      //跳转搜索页面
      window.open('/webview/bszn/search/search.html?' + 'Keyword=' + userSearchVal + '&p_region_code=' + curQh + '&curText=' + curText);
    }

  });
  //点击最近搜索
  $('#latelySearhList').on('click', 'li', function () {
    var tex = $(this).text()
    //跳转搜索页面
    var zjSearchUal = '/webview/bszn/search/search.html?' + 'Keyword=' + tex + '&p_region_code=' + curQh + '&curText=' + curText
    window.open(zjSearchUal)
  })
  var bmlist = []
  // 获取 区划 和 部门
  function queryQhBmData(code) {

    selectedBoxClickFlag = false;
    //区划数据
    $.ajax({
      url: '/web/bszn/region/findRegionList.jspc',
      dataType: "json",
      type: "POST",
      ContentType: "application/x-www-form-urlencoded",
      data: {
        'parent_code': code
      },
      success: function (res) {
        selectedBoxClickFlag = true;
        // console.log(res)
        if (res.code == '1') {
          var qhData = res.data
          // console.log(qhData)
          var quHtml = ''
          let objNameCode = {
            "420222040400": "𣲗山村委会",
            "420222040000": "𣲗源口镇",
            "420222042100": "𣲗源口村委会",
          }
          for (var i = 0; i < qhData.length; i++) {
            let name = qhData[i].NAME
            if (objNameCode[qhData[i].CODE]) {
              name = objNameCode[qhData[i].CODE]
            }
            quHtml += '<li title="' + name + '"><a href="javascript:;" code="' + qhData[i].CODE + '" grade="' + qhData[i].GRADE + '">' + name + '</a></li>'
          }
          $('#selectedBox_h').html(quHtml)
        } else {
          // console.log('获取数据失败')
        }
      },
      error: function () {
        selectedBoxClickFlag = true;
        // console.log('获取数据失败')
      }
    })
    //部门数据
    $.ajax({
      url: '/web/bszn/dept/findDeptList.jspc',
      dataType: "json",
      type: "POST",
      ContentType: "application/x-www-form-urlencoded",
      data: {
        'region_code': code
      },
      success: function (res) {
        bmlist = res.data
        // console.log(res)
        if (res.code == '1') {
          var bmData = res.data
          var bmHtml = ''
          let objNameCode = {
            "420222040400": "𣲗山村委会",
            "420222040000": "𣲗源口镇",
            "420222042100": "𣲗源口村委会"
          }
          for (var i = 0; i < bmData.length; i++) {
            let SHORT_NAME = bmData[i].SHORT_NAME
            if (objNameCode[bmData[i].REGION_CODE]) SHORT_NAME = objNameCode[bmData[i].REGION_CODE]
            bmHtml += '<li title="' + bmData[i].NAME + '"><a href="javascript:;" shortName="' + SHORT_NAME + '" code="' + bmData[i].CODE + '">' + SHORT_NAME + '</a></li>'
          }
          $('#bumenList_h').html(bmHtml)
        } else {
          // console.log('获取数据失败')
        }
      },
      error: function () {
        // console.log('获取数据失败')
      }
    })
  }
  //获取最近搜索 并展示
  function getlatelySearhBox() {
    var keywordArr = localStorage.getItem('gzj') ? JSON.parse(localStorage.getItem('gzj')) : [];
    if (keywordArr.length > 0) {
      var latelySearhHtml = ''
      var reg_x = /alert|and|exec|execute|update|count|truncate|declare|sitename|netuser|xp_cmdshell|like\'|insert|create|drop|table|grant|group_concat|column_name|prompt|ID_PAYLOAD|PAYLOAD|confirm|onmouseenter|information_schema\.columns|table_schema|union|where|select|delete|order|by\'|char|declare|\'or|like|onmouseover|eval|function|\(\)|Function|onclick\%|\'\=\'|\'and\'|content\-type|ltrim\(|onclick=|window\[|\/\*\*\/|iframe|document|script|\<script\>|\"|\'|\。\/|ontoggle|\<details/g

      if (keywordArr.length > 5) {
        for (var j = 0; j < 5; j++) {
          if (reg_x.test(keywordArr[j])) {
            continue
          }
          latelySearhHtml += '  <li><a href="javascript:;">' + keywordArr[j] + '</a></li>'
        }
      } else {
        for (var j = 0; j < keywordArr.length; j++) {
          if (reg_x.test(keywordArr[j])) {
            continue
          }
          latelySearhHtml += '  <li><a  href="javascript:;">' + keywordArr[j] + '</a></li>'
        }
      }

      $('#latelySearhList').html(latelySearhHtml)
    } else {
      $('#latelySearhBox').hide()
    }
  }

  $('.r_top_cont_x').on('click', '.rmfw_li', function () {
    var rmfwUrl = $(this).attr('data-href')
    var isLogin = $(this).attr('data-isLogin')
    if (isLogin == 'true') {
      if (checkLogin(true, rmfwUrl)) {
        window.open(rmfwUrl)
      }
    } else {
      window.open(rmfwUrl)
    }
  })

  //获取特色服务
  function getTsserviceData() {
    $.ajax({
      url: '/web/bmfw/tsfw_item/tsItemList.jspc',
      dataType: "json",
      type: "POST",
      ContentType: "application/x-www-form-urlencoded",
      data: {
        'region_code': regionCode_x + '000000',
        'region_grade': isCurGrade,
        'allData': 1
      },
      success: function (res) {
        if (res.code == '1') {
          var tsFw = res.data;
          if (tsFw != 0) {
            var new_tsfw = res.data;
            if (regionCode_x + '000000' == '420000000000') {
              var tsFw = res.data.slice(0, 5);

              var tsbmHtml = '<li url="javascript:;" style="position:relative" title="教育培训服务"><a class="jyfw_a" href="javascript:;">教育培训服务</a><span class="jyfw_tsfw" style="width:560px">\
                        <a style="width:50%" href="https://www.hbbys.com.cn" rel="noopener noreferrer" target="_blank" class="jyfw_item tsfwType" data-clickId="202011031600115">高校毕业生就业指导服务</a>\
                        <a style="width:50%" href="http://www.hbea.edu.cn/" rel="noopener noreferrer" target="_blank" class="jyfw_item tsfwType" data-clickId="202011031600116">教育考试服务</a>\
                        <a style="width:50%" href="https://jy.hbsis.gov.cn/#/visitor/index" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600123">应急管理公益培训</a>\
                        </span></li>'

              //     tsbmHtml += '<li url="javascript:;" style="position:relative" title="水利特色服务"><a class="jyfw_a" href="javascript:;">水利特色服务</a><span class="jyfw_tsfw" style="width:560px;left:unset;right:0">\
              // <a style="width:50%" href="/dsbmfw/420500yc/djdhsq/index.html" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600124">大江大河水情</a>\
              // <a style="width:50%" href="/dsbmfw/420500yc/slkp/index.html" rel="noopener noreferrer" target="_blank" class="jyfw_item tsfwType" data-clickId="202011031600125">水利科普知识</a>\
              // <a style="width:50%" href="/dsbmfw/420500yc/zysksq/index.html" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600126">重要水库水情</a>\
              // </span></li>'

              // 由于水利特色服务被屏蔽样式发生了改变 下面是原有样式
              // <li url="javascript:;" style="position:relative" title="便民特色服务"><a class="jyfw_a" href="javascript:;">便民特色服务</a><span class="jyfw_tsfw" style="width:560px"></span>
              // 现在改成 width:560px;left:unset;right:0

              tsbmHtml += '<li url="javascript:;" style="position:relative" title="便民特色服务"><a class="jyfw_a" href="javascript:;">便民特色服务</a><span class="jyfw_tsfw" style="width:560px;left:unset;right:0">\
                        <a style="width:50%" href="/dsbmfw/422822es/dlbzsb/index.html" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600127">地理标志商标产品查询</a>\
                        <a style="width:50%" href="/dsbmfw/429005qj/qj_pc_fxlydpcx/index.html" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600128">放心粮油店铺查询</a>\
                        <a style="width:50%" href="/dsbmfw/429005qj/qj_pc_smsh/index.html" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600129">市民生活</a>\
                        <a style="width:50%" href="/dsbmfw/429005qj/qj_pc_ygycxxcx/index.html" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600130">一馆一处信息查询</a>\
                        <a style="width:50%" href="/dsbmfw/421000jz/jz-lyjd/index.html" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600131">旅游景点</a>\
                        <a style="width:50%" href="/dsbmfw/421000jz/jz-bwg/index.html" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600132">博物馆查询</a>\
                        <a style="width:50%" href="/dsbmfw/420900xg/xg-jdcjszcx/index.html" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600133">机动车驾驶证查询</a>\
                        <a style="width:50%" href="/dsbmfw/420900xg/txrycx/index.html" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600134">退休人员查询</a>\
                        </span></li>'

              tsbmHtml += '<li url="javascript:;" style="position:relative" title="社会组织年度检查"><a class="jyfw_a" href="javascript:;">社会组织年度检查</a><span class="jyfw_tsfw" style="width:560px">\
                            <a style="width:50%" href="http://zwfw.hubei.gov.cn:8503/xcms/uias_login.do?appCode=mztshzzwsbsdt&gotoUrl=shzz/nj/st/njRecordList/shzz_nj_list.jhtml" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600135">对社会团体进行年度检查</a>\
                            <a style="width:50%" href="http://zwfw.hubei.gov.cn:8503/xcms/uias_login.do?appCode=mztshzzwsbsdt&gotoUrl=shzz/nj/mf/njRecordList/shzz_mfnj_list.jhtml" target="_blank" rel="noopener noreferrer" class="jyfw_item tsfwType" data-clickId="202011031600136">对民办非企业单位进行年度检查</a>\
                            </span></li>'
              // <a href="http://zbxx.e21.cn/" target="_blank" rel="noopener noreferrer" class="jyfw_item">教育技术装备管理服务</a><a href="http://shqb.e21.cn/" target="_blank" rel="noopener noreferrer" class="jyfw_item">学校后勤保障服务</a><a href="http://www.hbbys.com.cn" target="_blank" rel="noopener noreferrer" class="jyfw_item">高校毕业生就业指导服务</a><a href="http://zzpt.e21.cn/" target="_blank" rel="noopener noreferrer" class="jyfw_item">学生资助管理</a><a href="http://www.hbei.org.cn" target="_blank" rel="noopener noreferrer" class="jyfw_item">教育对外交流服务</a><a href="http://zsxx.e21.cn/" rel="noopener noreferrer" target="_blank" class="jyfw_item">高等学校招生服务</a><a href="http://www.hbea.edu.cn/" target="_blank" rel="noopener noreferrer" class="jyfw_item">教育考试服务</a><a href=" http://www.e21.cn/" target="_blank" rel="noopener noreferrer" class="jyfw_item">教育信息化服务</a>
            } else {
              var tsFw = res.data.slice(0, 8);
              var tsbmHtml = ''
            }
            var new_tsfw_html = ""
            for (var i = 0; i < tsFw.length; i++) {
              tsbmHtml += '<li title=' + tsFw[i].tname + '><a class="tsfwType" onclick="tsFwSkip(this)" data-isLogin="' + tsFw[i].isLogin + '" data-clickId="' + tsFw[i].tid + '" data-url="' + tsFw[i].url + '" href="javascript:;" >' + tsFw[i].tname + '</a></li>';
              new_tsfw_html += '<li url="' + tsFw[i].url + '" title="' + tsFw[i].tname + '" tid="' + tsFw[i].tid + '" class="sl_item" data-isLogin="' + tsFw[i].isLogin + '">' + tsFw[i].tname + '</li>';
            }
            $('.tsfw_list').html(tsbmHtml)
            $('.special_list').html(new_tsfw_html)
          }
        } else {
          // console.log('获取数据失败')
        }
      },
      error: function () {
        // console.log('获取数据失败')
      }
    })
  }
  var dictionaryArr = []
  var dictionaryCode=''
  var dictionaryName=''
  var dictionartList = []
  // 获取个人、法人生命周期分类
  function getdictionary(e){
    $.ajax({
      url: '/shspace/callinterface/dictionary?parentcode='+e,
      data: {},
      type: 'get',
      dataType: "json",
      ContentType: "application/x-www-form-urlencoded",
      success: function (res) {
        // console.log(res,'生命周期')
        dictionaryArr = dictionaryArr.concat(res)
        // console.log(dictionaryArr,'dic')
      }
    })
  }
  // 搜索输入框联想词
  function getKeyword(data) {
    console.log(data,dictionaryArr,'data')
    dictionaryCode=''
    dictionaryName=''
    for(let i=0;i<dictionaryArr.length;i++){
      if(dictionaryArr[i].name==data.keyword){
        console.log(i,dictionaryArr[i].code,dictionaryArr[i].name)
        dictionaryCode = dictionaryArr[i].code
        dictionaryName = dictionaryArr[i].name
      }
    }
    console.log(dictionaryCode,dictionaryName)
    if(data.keyword){
      if(dictionaryName){
        var url_dic = '/shspace/ybsl/unionprocess?offset=0&limit=10&rootCode=lbfl&name='+'&category='+dictionaryCode
      }else{
        var url_dic = '/shspace/ybsl/unionprocess?offset=0&limit=10&rootCode=lbfl&name='+data.keyword+'&category='+dictionaryCode
      }
      $.ajax({
        url: url_dic,
        data: {},
        type: 'get',
        dataType: "json",
        ContentType: "application/x-www-form-urlencoded",
        success: function (res) {
          console.log(JSON.parse(res.message),'一件事事项')
          dictionartList = JSON.parse(res.message).data
            var REstr1 = new RegExp(data.keyword, 'g')
                  var str1 = '<i>' + data.keyword + '</i>'
                  var html_lxc1 = '';
            for (var i = 0; i < dictionartList.length; i++) {
              var element1 =dictionartList[i].name;
              var tiaojian1 = element1.replace(REstr1, str1);
              if(dictionaryName){
                var bqBox = "<span class='bqStyle'>"+dictionaryName+"</span>"
                tiaojian1 = tiaojian1+bqBox
              }
              
              html_lxc1 += "<li class='searchLx_li' title='" + element1 + "'>" + tiaojian1 + "</li>"
            }
            $('.searchLx').html('')
            if(dictionartList.length>0){
              $('.searchLx').html(html_lxc1)
            $('.searchLx').show()
            }
            
            console.log(dictionartList)
            if(dictionartList.length==10){

            }else{
              $.ajax({
                url: '/web/search-v2/searchv2/web/portalHomePageSearch/prek',
                data: data,
                type: 'post',
                dataType: "json",
                ContentType: "application/json",
                success: function (res) {
                  if (res.code == 1) {
                    // 防止报错
                    if (res.data == null&&dictionartList.length==0) {
                      $('.searchLx').hide()
                      return;
                    }
                    var arrlength = 0
                    arrlength = 10-dictionartList.length
                    if(arrlength>res.data.length){
                      arrlength = res.data.length
                    }
                    var REstr = new RegExp(data.keyword, 'g')
                    var str = '<i>' + data.keyword + '</i>'
                    var html_lxc = '';
                    for (var i = 0; i < arrlength; i++) {
                      var element = res.data[i];
                      console.log(element,'element')
                      var tiaojian = element.replace(REstr, str);
                      html_lxc += "<li class='searchLx_li' title='" + element + "'>" + tiaojian + "</li>"
                    }
                    $('.searchLx').append(html_lxc)
                    $('.searchLx').show()
                  }
                }
              })
            }
          
        }
      })
    }else{
      $('.searchLx').html('')
      $('.searchLx').hide()
    }
    
  }

  // 一下为搜索逻辑js
  // 输入过滤器
  var inputFlag = false
  // 输入事件 包含汉字拼合
  $(document).on('compositionstart', '#searchVal_index', function (e) {
    inputFlag = true
  }).on('input', '#searchVal_index', function (e) {
    if (!inputFlag) {
      updateKeyword()
    }
  }).on('compositionend', '#searchVal_index', function (e) {
    inputFlag = false
    updateKeyword()
  })


  // 输入定时器
  var keywordTimeout = false

  function updateKeyword() {
    var data = {}
    data.keyword = $('#searchVal_index').val().trim().substr(0, 128)
    var wordLength = data.keyword.length
    if(data.keyword==''){
      $('.searchLx').hide();
      $('.searchLx').html('');
    }
    if (wordLength >= 128) {
      $('.total_word').addClass('active_x').siblings().hide()
    } else {
      $('.total_word').removeClass('active_x').siblings().show()
      $('.inp_word').text(wordLength)
    }
    keywordTimeout && clearTimeout(keywordTimeout)
    keywordTimeout = setTimeout(function () {
      keywordTimeout = false
      getKeyword(data)
    }, 100)
  }
  $("#searchVal_index").click(function () {
    stopPropagationByBrowser();
  })
  $('body').on('click', function () {
    $('.searchLx').hide();
  })

  $('.searchLx').on('click', '.searchLx_li', function () {
    keyword = $(this).attr('title');
    $('.searchLx').hide();
    $('#searchVal_index').val(keyword)
    $('.inp_word').text(keyword.length)
    $('#searchBtn_index').click()
  })

  $("#searchVal_index").focus(function () {
    var data = {}
    data.keyword = $('#searchVal_index').val().trim()
    getKeyword(data)
  });

  //部门的显示与隐藏    新增区划等级为5/6显示事项
  function isBumenShow(num) {
    if (num == 5 || num == 6) {
      $('.bumen').hide()
      $('.sxbox').show()
      getItemList()
    } else {
      $('.bumen').show()
      $('.sxbox').hide()
    }
  }




  // 选择区划重置特色服务区划联动
  $('.ss_city_btn').click(function () {
    // console.log($(this).html(), 'qwe')
    $('.ss_city_name').html($(this).html())
    $(".ss_city_box").hide();
    regionCode_x = $(this).attr('val').substr(0, 6)
    isCurGrade = $(this).attr('grade')
    setSessionRegionCode($(this).attr('val'), $(this).html(), $(this).attr('grade'));
    setSessionDeptCode('', '', '请选择区划');
    // console.log(regionCode_x)
    getTsserviceData()
    window.location.reload()
  })
  $('.special_list').on('click', '.sl_item', function () {
    // console.log('点击办事')
    let url = $(this).attr('url')
    let tid = $(this).attr('tid')
    let title = $(this).attr('title')
    let isPower = $(this).attr('data-isLogin')
    let modular = '特色服务'
    let curHrefUrl = window.location.href //验证登录时的当前地址
    if (typeof isPower != '0' && isPower != 0) {
      // 1.验证是否登录
      if (checkLogin(true, curHrefUrl)) {
        // 2.验证用户类型
        var userInfo = getCurrentOnlineUserInfo();
        if (isPower == '2') { // 须个人登录
          if (userInfo.usertype == '1') { // 个人
            // getNativeIp(tid,title,url,modular)
            window.open(url);
          } else {
            layer.msg("您当前是以法人账号登录，无法办理自然人相关业务。", {
              icon: 5
            });
          }
        } else if (isPower == '3') { // 须法人登录
          if (userInfo.usertype == '2') { // 法人
            // getNativeIp(tid,title,url,modular)
            window.open(url);
          } else {
            layer.msg("您当前是以自然人账号登录，无法办理法人相关业务。", {
              icon: 5
            });
          }
        } else { // 须登录
          // getNativeIp(tid,title,url,modular)
          window.open(url);
        }
      }
    } else {
      // getNativeIp(tid,title,url,modular)
      window.open(url);
    }
  })

  // $('.ssbox').on('click', '.more_ss', function () {
  //     console.log('点击办事')
  //     window.open('/webview/tsfw/tsfw.html')
  // })
  $('.more_ss').click(function () {
    // console.log('点击办事')
    window.open('/webview/tsfw/tsfw.html')
  })

})

function openReduDetailWindow(code, parentCode, serviceObj) {
  window.open("/webview/bszn/grfw/redu/redudetail.html?code=" + code + "&parentcode=" + parentCode + "&serviceObject=" + serviceObj);
}

var selectCode;
var selectParentCode;
var serviceObject;

function openReduListWindow(code, parentCode, serviceObj) {
  event.stopPropagation();
  var regionGrade = getSessionStorageData("p_region_grade");
  serviceObject = serviceObj;
  if ("2" == regionGrade) {
    selectCode = code;
    selectParentCode = parentCode;
    $(".zgc").show();

  } else {
    var regionCode = getSessionStorageData("p_region_code");
    window.open("/webview/bszn/grfw/redu/redulist.html?code=" + code + "&parentcode=" + parentCode + "&serviceObject=" + serviceObj + "&regionCode=" + regionCode);
  }
}

function searchCity(obj) {
  var selectRegionCode = $(obj).attr("code");
  var selectRegionName = $(obj).attr("name");
  var selectRegionGrade = $(obj).attr("grade");
  //updateGlobalRegion(selectRegionCode, selectRegionName, selectRegionGrade);
  setSessionRegionCode(selectRegionCode, selectRegionName, selectRegionGrade);
  window.location.href = "/webview/bszn/grfw/redu/redulist.html?code=" + selectCode + "&parentcode=" + selectParentCode + "&serviceObject=" + serviceObject + "&regionCode=" + selectRegionCode;
}

function closeModel() {
  $(".zgc").hide();
}


var regionUrl_x = [{
  areaId: '420000',
  text: '湖北省人民政府',
  url: 'https://www.hubei.gov.cn/'
},
{
  areaId: '420100',
  text: '武汉市人民政府',
  url: 'http://www.wuhan.gov.cn'
},
{
  areaId: '420600',
  text: '襄阳市人民政府',
  url: 'http://www.xiangyang.gov.cn'
},
{
  areaId: '420500',
  text: '宜昌市人民政府',
  url: 'https://www.yichang.gov.cn'
},
{
  areaId: '420700',
  text: '鄂州市人民政府',
  url: 'http://www.ezhou.gov.cn'
},
{
  areaId: '421100',
  text: '黄冈市人民政府',
  url: 'http://www.hg.gov.cn'
},
{
  areaId: '420200',
  text: '黄石市人民政府',
  url: 'http://www.huangshi.gov.cn'
},
{
  areaId: '421200',
  text: '咸宁市人民政府',
  url: 'http://www.xianning.gov.cn'
},
{
  areaId: '420900',
  text: '孝感市人民政府',
  url: 'https://www.xiaogan.gov.cn'
},
{
  areaId: '420300',
  text: '十堰市人民政府',
  url: 'http://www.shiyan.gov.cn'
},
{
  areaId: '421000',
  text: '荆州市人民政府',
  url: 'http://www.jingzhou.gov.cn'
},
{
  areaId: '420800',
  text: '荆门市人民政府',
  url: 'https://www.jingmen.gov.cn'
},
{
  areaId: '421300',
  text: '随州市人民政府',
  url: 'http://www.suizhou.gov.cn'
},
{
  areaId: '422800',
  text: '恩施州人民政府',
  url: 'http://www.enshi.gov.cn'
},
{
  areaId: '429004',
  text: '仙桃市人民政府',
  url: 'http://www.xiantao.gov.cn'
},
{
  areaId: '429006',
  text: '天门市人民政府',
  url: 'https://www.tianmen.gov.cn'
},
{
  areaId: '429005',
  text: '潜江市人民政府',
  url: 'http://www.hbqj.gov.cn'
},
{
  areaId: '429021',
  text: '神农架林区人民政府',
  url: 'http://www.snj.gov.cn'
}
]
var regionCode_x = sessionStorage.getItem('p_region_code') || '420000'
var regionName_x = sessionStorage.getItem('p_region_name') || '湖北省'
var regionGrade_x = sessionStorage.getItem('p_region_grade') || '2'

regionCode_x = regionCode_x.substr(0, 6)
if (regionCode_x == '429004' || regionCode_x == '429006' || regionCode_x == '429005' || regionCode_x == '429021') {
  regionCode_x = regionCode_x
} else {
  regionCode_x = regionCode_x.substr(0, 4) + '00'
}
for (var i = 0; i < regionUrl_x.length; i++) {
  var element = regionUrl_x[i];
  if (regionCode_x == element.areaId) {
    $('#tzrmzf_x').find('a').attr({
      'href': element.url,
      'target': '_blank'
    }).text(element.text)
    if (regionCode_x == '429021') {
      var slogan_text = element.text.substr(0, 3) + '政务欢迎您'
    } else {
      var slogan_text = element.text.substr(0, 2) + '政务欢迎您'
    }
    $('.index_ehb > span').text(slogan_text)
    // $('.index_ehb').css('font-size','30px')
    // $('.index_ehb').text('深切悼念新冠肺炎疫情牺牲烈士和逝世同胞')
  }
}
// 建党100周年头部皮肤

var imgUrl_x = './images/' + regionCode_x + '.jpg'


window.screenWidth = $(window).width()
if (regionCode_x == '420000' && screenWidth <= 1024) {
  var imgUrl_x = './images/bg-42000_7682x.png';
  // var imgUrl_x = './images/bg-42000_7682x.png'; //默哀模式头图
} else if (regionCode_x == '420000') {
  var imgUrl_x = './images/bg-420002x.png';
}
// var imgUrl_x = './images/bg-42000@2x_gray.png'; //默哀模式头图

// var imgUrl_x = "/images/index/bg_jd100.png";
$('.header').css({
  'background': 'url(' + imgUrl_x + ') center no-repeat',
  'background-size': 'cover'
})

//新换头部
$(window).resize(function () {
  if ($(window).width() < 768 && regionCode_x == '420000') {
    // var imgUrl_x = './images/bg-42000_7682x.png';
    var imgUrl_x = './images/bg-42000_7682x.png'; //默哀模式头图
    $('.header').css({
      'background': 'url(' + imgUrl_x + ') center no-repeat',
      'background-size': 'cover'
    })
    $('.heyun').hide();
  } else if (regionCode_x == '420000') {

    // console.log($(window).width(), '$(window).width()')
    // var imgUrl_x = './images/bg-420002x.png'
    var imgUrl_x = './images/bg-420002x.png'; //默哀模式头图
    $('.header').css({
      'background': 'url(' + imgUrl_x + ') center no-repeat',
      'background-size': 'cover'
    })
    $('.heyun').show();
  }
});

var mySwiper_gr, mySwiper_fr, mySwiper_bm;
// 按个人初始化
// type_init("/web/bszn/find/infoToProjectTitle.jspc", { user_type: 1 }, mySwiper_gr, 'swiper_gr', '#pagination_gr')
// 按法人初始化
// type_init({ user_type: 2 }, mySwiper_fr ,'swiper_fr', '#pagination_fr')

function type_init(url, user_typeData, mySwiper, swiper, pagination) {
  var screenWidth = $(window).width(),
    bm_total, grfr_total;
  //   console.log(screenWidth);
  if (screenWidth > 1024) {
    bm_total = 16
    grfr_total = 12
  } else if (screenWidth <= 1024) {
    bm_total = 16
    grfr_total = 12
  }
  if (user_typeData.user_type == '1') {
    var res = {
      code: 1,
      status: 200,
      msg: "操作成功",
      data: [{
        PC_ICON: "/images/gr_zt_sysy.png",
        CODE: "005",
        SERVICE_OBJECT: "1",
        NAME: "生育收养"
      },
      {
        PC_ICON: "/images/gr_zt_hjbl.png",
        CODE: "010",
        SERVICE_OBJECT: "1",
        NAME: "户籍办理"
      },
      {
        PC_ICON: "/images/gr_zt_mzzj.png",
        CODE: "015",
        SERVICE_OBJECT: "1",
        NAME: "民族宗教"
      },
      {
        PC_ICON: "/images/gr_zt_kyjy.png",
        CODE: "020",
        SERVICE_OBJECT: "1",
        NAME: "教育科研"
      },
      {
        PC_ICON: "/images/gr_zt_rwfy.png",
        CODE: "025",
        SERVICE_OBJECT: "1",
        NAME: "入伍服役"
      },
      {
        PC_ICON: "/images/gr_zt_cyjy.png",
        CODE: "030",
        SERVICE_OBJECT: "1",
        NAME: "就业创业"
      },
      {
        PC_ICON: "/images/gr_zt_slbg.png",
        CODE: "035",
        SERVICE_OBJECT: "1",
        NAME: "设立变更"
      },
      {
        PC_ICON: "/images/gr_zt_zyzb.png",
        CODE: "040",
        SERVICE_OBJECT: "1",
        NAME: "准营准办"
      },
      {
        PC_ICON: "/images/gr_zt_dyzy.png",
        CODE: "045",
        SERVICE_OBJECT: "1",
        NAME: "抵押质押"
      },
      {
        PC_ICON: "/images/gr_zt_zyzg.png",
        CODE: "050",
        SERVICE_OBJECT: "1",
        NAME: "职业资格"
      },
      {
        PC_ICON: "/images/gr_zt_xzjf.png",
        CODE: "055",
        SERVICE_OBJECT: "1",
        NAME: "行政缴费"
      },
      {
        PC_ICON: "/images/gr_zt_hydj.png",
        CODE: "060",
        SERVICE_OBJECT: "1",
        NAME: "婚姻登记"
      },
      {
        PC_ICON: "/images/gr_zt_ydfx.png",
        CODE: "065",
        SERVICE_OBJECT: "1",
        NAME: "优待抚恤"
      },
      {
        PC_ICON: "/images/gr_zt_ghjs.png",
        CODE: "070",
        SERVICE_OBJECT: "1",
        NAME: "规划建设"
      },
      {
        PC_ICON: "/images/gr_zt_zfbz.png",
        CODE: "075",
        SERVICE_OBJECT: "1",
        NAME: "住房保障"
      },
      {
        PC_ICON: "/images/gr_zt_shbz.png",
        CODE: "085",
        SERVICE_OBJECT: "1",
        NAME: "社会保障"
      },
      {
        PC_ICON: "/images/gr_zt_zjbl.png",
        CODE: "090",
        SERVICE_OBJECT: "1",
        NAME: "证件办理"
      },
      {
        PC_ICON: "/images/gr_zt_jtcx.png",
        CODE: "095",
        SERVICE_OBJECT: "1",
        NAME: "交通出行"
      },
      {
        PC_ICON: "/images/gr_zt_ggly.png",
        CODE: "100",
        SERVICE_OBJECT: "1",
        NAME: "旅游观光"
      },
      {
        PC_ICON: "/images/gr_zt_cjrj.png",
        CODE: "105",
        SERVICE_OBJECT: "1",
        NAME: "出境入境"
      },
      {
        PC_ICON: "/images/gr_zt_xfwq.png",
        CODE: "110",
        SERVICE_OBJECT: "1",
        NAME: "消费维权"
      },
      {
        PC_ICON: "/images/gr_zt_ggaq.png",
        CODE: "115",
        SERVICE_OBJECT: "1",
        NAME: "公共安全"
      },
      {
        PC_ICON: "/images/gr_zt_sfgz.png",
        CODE: "120",
        SERVICE_OBJECT: "1",
        NAME: "司法公证"
      },
      {
        PC_ICON: "/images/gr_zt_zscq.png",
        CODE: "125",
        SERVICE_OBJECT: "1",
        NAME: "知识产权"
      },
      {
        PC_ICON: "/images/gr_zt_hblh.png",
        CODE: "130",
        SERVICE_OBJECT: "1",
        NAME: "环保绿化"
      },
      {
        PC_ICON: "/images/gr_zt_whty.png",
        CODE: "135",
        SERVICE_OBJECT: "1",
        NAME: "文化体育"
      },
      {
        PC_ICON: "/images/gr_zt_gysy.png",
        CODE: "140",
        SERVICE_OBJECT: "1",
        NAME: "公用事业"
      },
      {
        PC_ICON: "/images/gr_zt_ylws.png",
        CODE: "145",
        SERVICE_OBJECT: "1",
        NAME: "医疗卫生"
      },
      {
        PC_ICON: "/images/gr_zt_lztx.png",
        CODE: "150",
        SERVICE_OBJECT: "1",
        NAME: "离职退休"
      },
      {
        PC_ICON: "/images/gr_zt_swbz.png",
        CODE: "155",
        SERVICE_OBJECT: "1",
        NAME: "死亡殡葬"
      },
      {
        PC_ICON: "/images/gr_zt_qt.png",
        CODE: "999",
        SERVICE_OBJECT: "1",
        NAME: "其他"
      }
      ]

    }
    if (res.code == 1) {
      swiper = '#' + swiper;
      $(swiper).find('.loading_x').hide()
      var count = res.data.length; // 获取总数
      if (user_typeData.user_type) { // 个人法人传此参数
        var pageTotal = Math.ceil(count / grfr_total) // 获取总页数
        for (var i = 0; i < pageTotal; i++) {
          var swiper_slide = document.createElement('div')
          $(swiper_slide).attr('class', 'swiper-slide')
          $(swiper).find('.swiper-wrapper').append(swiper_slide)
        }
        if (user_typeData.user_type == 1) {
          var url_grfr = '/webview/fw/grfw.html?type=zt&code='
        } else if (user_typeData.user_type == 2) {
          var url_grfr = '/webview/fw/frfw.html?type=zt&code='
        }
        for (var m = 0; m < pageTotal; m++) {
          var slideLiHtml = '<ul class="clearfix">'
          for (var j = 0; j < res.data.length; j++) {
            var element = res.data[j];
            if (Math.floor(j / grfr_total) == m) {
              slideLiHtml += '<li><a target="_blank" rel="noopener noreferrer" href="' + url_grfr + element.CODE + '"><img src="' + element.PC_ICON + '" height="54px" alt=""><p>' + element.NAME + '</p></a></li>'
            }
          }
          slideLiHtml += '</ul>'
          $(swiper).find('.swiper-wrapper').find('.swiper-slide').eq(m).html(slideLiHtml)
        }
      } else { // 部门不传此参数
        var pageTotal_bm = Math.ceil(count / bm_total) // 获取总页数
        for (var i = 0; i < pageTotal_bm; i++) {
          var swiper_slide = document.createElement('div')
          $(swiper_slide).attr('class', 'swiper-slide')
          $(swiper).find('.swiper-wrapper').append(swiper_slide)
        }
        let objNameCode = {
          "420222040400": {
            "SHORT_NAME": "𣲗山村委会",
            "NAME": "𣲗山村村民委员会",
          },
          "420222040000": {
            "SHORT_NAME": "𣲗源口镇",
            "NAME": "𣲗源口镇人民政府",
          },
          "420222042100": {
            "SHORT_NAME": "𣲗源口村委会",
            "NAME": "𣲗源口村村民委员会",
          }
        }
        // console.log('123')
        var url_bm = '/webview/bszn/bmsy.html?department='
        for (var m = 0; m < pageTotal_bm; m++) {
          var slideLiHtml = '<ul class="type_bm clearfix">'
          for (var j = 0; j < res.data.length; j++) {
            var element = res.data[j];
            if (Math.floor(j / bm_total) == m) {
              let SHORT_NAME = element.SHORT_NAME
              let NAME = element.NAME
              if (objNameCode[element.REGION_CODE]) {
                SHORT_NAME = objNameCode[element.REGION_CODE].SHORT_NAME
                NAME = objNameCode[element.REGION_CODE].NAME
              }
              slideLiHtml += '<li><a target="_blank" rel="noopener noreferrer" href="' + url_bm + element.CODE + '" title="' + NAME + '">' + SHORT_NAME + '</a></li>'
            }
          }
          slideLiHtml += '</ul>'
          $(swiper).find('.swiper-wrapper').find('.swiper-slide').eq(m).html(slideLiHtml)
        }

      }
      mySwiper = new Swiper(swiper, {
        // loop: true, // 循环模式选项
        navigation: {
          nextEl: '#button-next-gr',
          prevEl: '#button-prev-gr',
          disabledClass: 'my-button-disabled',
        },
        // 如果需要分页器
        pagination: {
          el: pagination,
          clickable: true,
        },
        observer: true,
        observerParents: true,
      })
      mySwiper.el.onmouseover = function () {
        mySwiper.navigation.$nextEl.removeClass('hide');
        mySwiper.navigation.$prevEl.removeClass('hide');
      }
      mySwiper.el.onmouseout = function () {
        mySwiper.navigation.$nextEl.addClass('hide');
        mySwiper.navigation.$prevEl.addClass('hide');
      }
    } else {
      // console.log(res.msg);
    }


  } else {

    $.ajax({
      type: "POST",
      url: url,
      data: user_typeData, //接口上个人是1  法人是2
      dataType: "json",
      success: function (res) {
        if (res.code == 1) {
          swiper = '#' + swiper;
          $(swiper).find('.loading_x').hide()
          var count = res.data.length; // 获取总数
          if (user_typeData.user_type) { // 个人法人传此参数
            var pageTotal = Math.ceil(count / grfr_total) // 获取总页数
            for (var i = 0; i < pageTotal; i++) {
              var swiper_slide = document.createElement('div')
              $(swiper_slide).attr('class', 'swiper-slide')
              $(swiper).find('.swiper-wrapper').append(swiper_slide)
            }
            if (user_typeData.user_type == 1) {
              var url_grfr = '/webview/fw/grfw.html?type=zt&code='
            } else if (user_typeData.user_type == 2) {
              var url_grfr = '/webview/fw/frfw.html?type=zt&code='
            }
            for (var m = 0; m < pageTotal; m++) {
              var slideLiHtml = '<ul class="clearfix">'
              for (var j = 0; j < res.data.length; j++) {
                var element = res.data[j];
                if (Math.floor(j / grfr_total) == m) {
                  slideLiHtml += '<li><a target="_blank" rel="noopener noreferrer" href="' + url_grfr + element.CODE + '"><img src="' + element.PC_ICON + '" height="54px" alt=""><p>' + element.NAME + '</p></a></li>'
                }
              }
              slideLiHtml += '</ul>'
              $(swiper).find('.swiper-wrapper').find('.swiper-slide').eq(m).html(slideLiHtml)
            }
          } else { // 部门不传此参数
            var pageTotal_bm = Math.ceil(count / bm_total) // 获取总页数
            for (var i = 0; i < pageTotal_bm; i++) {
              var swiper_slide = document.createElement('div')
              $(swiper_slide).attr('class', 'swiper-slide')
              $(swiper).find('.swiper-wrapper').append(swiper_slide)
            }
            var url_bm = '/webview/bszn/bmsy.html?department='
            for (var m = 0; m < pageTotal_bm; m++) {
              var slideLiHtml = '<ul class="type_bm clearfix">'
              for (var j = 0; j < res.data.length; j++) {
                var element = res.data[j];
                if (Math.floor(j / bm_total) == m) {
                  slideLiHtml += '<li><a target="_blank" rel="noopener noreferrer" href="' + url_bm + element.CODE + '" title="' + element.NAME + '">' + element.SHORT_NAME + '</a></li>'
                }
              }
              slideLiHtml += '</ul>'
              $(swiper).find('.swiper-wrapper').find('.swiper-slide').eq(m).html(slideLiHtml)
            }

          }
          // console.log(user_typeData);
          var nextEl, prevEl;
          if (user_typeData.user_type == '2') {
            nextEl = '#button-next-fr'
            prevEl = '#button-prev-fr'
          } else {
            nextEl = '#button-next-bm'
            prevEl = '#button-prev-bm'
          }
          mySwiper = new Swiper(swiper, {
            // loop: true, // 循环模式选项
            navigation: {
              nextEl: nextEl,
              prevEl: prevEl,
              disabledClass: 'my-button-disabled',
            },
            // 如果需要分页器
            pagination: {
              el: pagination,
              clickable: true,
            },
            observer: true,
            observerParents: true,
          })
          mySwiper.el.onmouseover = function () {
            mySwiper.navigation.$nextEl.removeClass('hide');
            mySwiper.navigation.$prevEl.removeClass('hide');
          }
          mySwiper.el.onmouseout = function () {
            mySwiper.navigation.$nextEl.addClass('hide');
            mySwiper.navigation.$prevEl.addClass('hide');
          }
        } else {
          // console.log(res.msg);
        }
      }
    })



  }

}


// 收费高频通用清单 点击事件
$('.SFGPListing').on('click', function () {
  var data = {}
  data.type = $(this).attr('data-type')
  data.region_code = sessionStorage.getItem('p_region_code') ? sessionStorage.getItem('p_region_code').substr(0, 6) : '420000';
  // console.log(data);
  $.ajax({
    url: '/web/bszn/zwgk/sfqd/initSfqdHtml.jspc',
    data: data,
    type: 'post',
    crossDomain: true,
    dataType: 'json',
    success: function (res) {
      if (res.code == 1) {
        if (res.data.path != '') {
          // window.location.href = res.data.path
          window.open(res.data.path)
        } else {
          // layer.msg("该类清单正在梳理中", { icon: 5 });
          if (data.type == '1') {
            var listingType = 'SF'
          } else if (data.type == '5') {
            var listingType = 'GP'
          }
          var url_SF = '/webview/zwgk/SFGPListing.html?type=' + listingType
          window.open(url_SF)
        }
      }
    }
  })
})


// 公安交管
function GAJG_ajax() {
  var userId = window.uias_userid
  // console.log(userId);
  // var GAJGUrl = '/web/tysl/HTTPSERVER_PROXY/gatweb.jspc?uuid=' + userId
  var GAJGUrl = "https://prod-gateway.ehbapp.hubei.gov.cn/5f9e05b4385c4bb884c911dfb8651847";

  // 临时***
  // $.ajax({
  //   url: GAJGUrl,
  //   type: 'post',
  //   headers: {
  //     "X-hbzw-Api-Key": "52279c17-c3f3-4662-bc40-707adb510fff"
  //   },
  //   data: {
  //     uuid: userId
  //   },
  //   crossDomain: true,
  //   success: function (res) {}
  // })
}

function tsFwSkip(obj) {
  var localUrl = location.href;
  var isLogin = $(obj).attr('data-islogin')
  var openUrl = $(obj).attr('data-url')
  if (isLogin == '1') {
    if (checkLogin(true, localUrl, true)) {
      //调用搜索关键字信息详情统计接口
      window.open(openUrl);
    }
  } else {
    window.open(openUrl)
  }
}

$(function () {


  $('.gogrkj_x').on('click', function () {
    toGrkjUrl(true)
  })

  //登录
  $('.login_x').on('click', function () {
    $('#login').click()
  })
  // 注册
  $('.register_x').on('click', function () {
    $('#register').click()
  })
  $('.man-login').on('click', function () {
    // console.log('点击登录')
    $('#login').click()
  })
  $('.man-reg').on('click', function () {
    // console.log('点击登录')
    $('#register').click()
  })
  // 按个人 按法人 按部门 tab
  var init_flag = true,
    bm_flag = true;
  var ysb_zt_autoplay = 0;
  $('.cen_top_title_item_x').on('click', function () {
    var firstLeft = $(this).parent().find('.cen_top_title_item_x').eq(0).offset().left;
    var thisLeft = $(this).offset().left
    $(this).siblings('.line_x').css('left', thisLeft - firstLeft)
    var lineWidth = $(this).width()
    $(this).siblings('.line_x').width(lineWidth)

    $(this).addClass('active').siblings().removeClass('active')
    var type = $(this).attr('data-type')
    switch (type) {
      case 'gr':
        $('.top_gr_x').show().siblings().hide()
        break;
      case 'fr':
        $('.top_fr_x').show().siblings().hide()
        if (init_flag) {
          init_flag = false;
          type_init("/web/bszn/find/infoToProjectTitle.jspc", {
            user_type: 2
          }, mySwiper_fr, 'swiper_fr', '#pagination_fr')
        }
        break;
      case 'bm':
        $('.top_bm_x').show().siblings().hide()
        if (bm_flag) {
          var p_region_code = sessionStorage.getItem('p_region_code') || '420000000000';
          bm_flag = false;
          // dept_init(p_region_code)
          type_init("/web/bszn/dept/findDeptList.jspc", {
            region_code: p_region_code
          }, mySwiper_bm, 'swiper_bm', '#pagination_bm')

        }
        break;
      case 'yslb':
        $('.top_yslb_x').show().siblings().hide()

        break;
      case 'zt':
        $('.top_zt_x').show().siblings().hide()
        mySwiper_zt = new Swiper('#swiper_zt', {
          loop: yslb_zt_Loop, // 循环模式选项
          autoplay: {
            disableOnInteraction: false,
            delay: ysb_zt_autoplay,
          },
          pagination: {
            el: '#pagination_zt',
            clickable: true,
          },
          slidesPerView: slidesPerView_ztlb, //'auto'
          allowTouchMove: allowTouchMove,
          paginationClickable: true,
          spaceBetween: 30,
          // 如果需要分页器
          // observer: true,
          // observerParents: true,
        })
        break;
      default:
        break;
    }
  })

  //特色服务 - 区划显示注入
  $('#tefw_qh').html(sessionStorage.getItem('p_region_name'))


  //便民服务登录类
  $('.login_a').on('click', function () {
    var url = $(this).attr('data-url');
    if (checkLogin(true, url)) {
      window.open(url)
    }
  })


  // 响应式特色服务hover改为点击
  $('.tsfw_list').on('click', '.jyfw_a', function () {
    event.stopPropagation()
    var docWidth = $('body').width()
    if (docWidth <= 1024) {
      $(this).siblings('.jyfw_tsfw').show().parent('li').siblings('li').find('.jyfw_tsfw').hide()
    }
  })

  $('.cyfwBtn').on('click', '.cyfwBtnItem', function () {
    event.stopPropagation()
    var docWidth = $('body').width();
    if (docWidth <= 1024) {
      $(this).find('.itemBox').toggle().parent('.cyfwBtnItem').siblings().find('.itemBox').hide();
    }


  })


  var navFlag = false;

  $(window).on('click', function () {
    $(".qrCode_wrap").hide();
    var screenWidth = $(window).width()
    if (screenWidth < 1024) {
      $('.jyfw_tsfw').hide()
      $('#navList').find('img').attr('src', '/common/layout/top/img/gncdan_header.png')
      $('#andy-nav').hide()
      navFlag = false;
    }
  })

  // 响应式导航栏开关
  $('#navList').on('click', function () {
    event.stopPropagation()
    if (!navFlag) {
      $(this).find('img').attr('src', '/common/layout/top/img/gbcd_header.png')
      $('#andy-nav').show()
    } else {
      $(this).find('img').attr('src', '/common/layout/top/img/gncdan_header.png')
      $('#andy-nav').hide()
    }
    navFlag = !navFlag
  })

  // 响应式用户登录 
  $('#screen_userImg').on('click', async function () {
    var url = await toGrkjUrl(false)
    if (checkLogin(false, url)) {
      window.location.href = url
    } else {
      topLogin()
    }
  })

  // 区划选择关闭按钮
  $('.gbBox_img').on('click', function () {
    $('#cityCode_h').hide()
  })

  $('.areaSelectDiv').on('click', function () {
    event.stopPropagation()
    $('.cityCode_h').show()
  })

  getHcpData()
  // 好差评数据
  function getHcpData() {
    var hcpRegion = regionCode_x + '000000'
    if (hcpRegion == '420000000000') {
      var code = '1'
    } else {
      var code = '2'
    }
    $.ajax({
      url: '/web/bszn/hcp/getCountListForeign.jspc',
      type: 'post',
      data: {
        "regionCode": hcpRegion,
        "code": code
      },
      crossDomain: true,
      success: function (res) {
        if (res.code == 1) {
          var hcpData = JSON.parse(res.data);
          $('.pjzs').text(hcpData.data.assessall)
          $('.zdpjs').text(hcpData.data.activeAssess)
          $('.myl').text(hcpData.data.mydl + '%')
          $('.cps').text(hcpData.data.cpzl)
          $('.cpzgl').text('100%')
        }
      }
    })

    // 暂时手动接口(高考后屏蔽)
    // var hcpData = [
    //     {
    //         regionName: "湖北省",
    //         regionCode: "420000000000",
    //         assessall: "988561",
    //         activeAssess: "988561",
    //         mydl: "99.99",
    //         cpzl: "96",
    //     },
    //     {
    //         regionName: "武汉市",
    //         regionCode: "420100000000",
    //         assessall: "333591",
    //         activeAssess: "333591",
    //         mydl: "99.99",
    //         cpzl: "17",
    //     },
    //     {
    //         regionName: "襄阳市",
    //         regionCode: "420600000000",
    //         assessall: "75421",
    //         activeAssess: "75421",
    //         mydl: "99.98",
    //         cpzl: "9",
    //     },
    //     {
    //         regionName: "宜昌市",
    //         regionCode: "420500000000",
    //         assessall: "54600",
    //         activeAssess: "54600",
    //         mydl: "99.99",
    //         cpzl: "2",
    //     },
    //     {
    //         regionName: "黄石市",
    //         regionCode: "420200000000",
    //         assessall: "11196",
    //         activeAssess: "11196",
    //         mydl: "99.97",
    //         cpzl: "3",
    //     },
    //     {
    //         regionName: "十堰市",
    //         regionCode: "420300000000",
    //         assessall: "53755",
    //         activeAssess: "53755",
    //         mydl: "99.97",
    //         cpzl: "14",
    //     },
    //     {
    //         regionName: "荆州市",
    //         regionCode: "421000000000",
    //         assessall: "69990",
    //         activeAssess: "69990",
    //         mydl: "99.98",
    //         cpzl: "7",
    //     },
    //     {
    //         regionName: "荆门市",
    //         regionCode: "420800000000",
    //         assessall: "50859",
    //         activeAssess: "50859",
    //         mydl: "100",
    //         cpzl: "0",
    //     },
    //     {
    //         regionName: "鄂州市",
    //         regionCode: "420700000000",
    //         assessall: "15743",
    //         activeAssess: "15743",
    //         mydl: "99.98",
    //         cpzl: "3",
    //     },
    //     {
    //         regionName: "孝感市",
    //         regionCode: "420900000000",
    //         assessall: "22463",
    //         activeAssess: "22463",
    //         mydl: "99.96",
    //         cpzl: "8",
    //     },
    //     {
    //         regionName: "黄冈市",
    //         regionCode: "421100000000",
    //         assessall: "24462",
    //         activeAssess: "24462",
    //         mydl: "99.98",
    //         cpzl: "3",
    //     },
    //     {
    //         regionName: "咸宁市",
    //         regionCode: "421200000000",
    //         assessall: "21135",
    //         activeAssess: "21135",
    //         mydl: "99.97",
    //         cpzl: "5",
    //     },
    //     {
    //         regionName: "随州市",
    //         regionCode: "421300000000",
    //         assessall: "21976",
    //         activeAssess: "21976",
    //         mydl: "100",
    //         cpzl: "0",
    //     },
    //     {
    //         regionName: "恩施州",
    //         regionCode: "422800000000",
    //         assessall: "158485",
    //         activeAssess: "158485",
    //         mydl: "99.99",
    //         cpzl: "3",
    //     },
    //     {
    //         regionName: "仙桃市",
    //         regionCode: "429004000000",
    //         assessall: "17619",
    //         activeAssess: "17619",
    //         mydl: "99.95",
    //         cpzl: "8",
    //     },
    //     {
    //         regionName: "天门市",
    //         regionCode: "429006000000",
    //         assessall: "33266",
    //         activeAssess: "33266",
    //         mydl: "99.99",
    //         cpzl: "1",
    //     },
    //     {
    //         regionName: "潜江市",
    //         regionCode: "429005000000",
    //         assessall: "17227",
    //         activeAssess: "17227",
    //         mydl: "99.98",
    //         cpzl: "2",
    //     },

    //     {
    //         regionName: "神农架",
    //         regionCode: "429021000000",
    //         assessall: "1977",
    //         activeAssess: "1977",
    //         mydl: "100",
    //         cpzl: "0",
    //     },

    // ]
    // for (var i = 0; i < hcpData.length; i++) {
    //     var element = hcpData[i];
    //     if (element.regionCode == hcpRegion) {
    //         $('.pjzs').text(element.assessall)
    //         $('.zdpjs').text(element.activeAssess)
    //         $('.myl').text(element.mydl + '%')
    //         $('.cps').text(element.cpzl)
    //         $('.cpzgl').text('100%')
    //     }
    // }


    $.ajax({
      url: '/web/external/itemBsNum/getNum',
      type: 'post',
      data: JSON.stringify({
        "qhdm": hcpRegion == '420000000000' ? '' : hcpRegion,
        "days": '30'
      }),
      contentType: "application/json",
      success: function (res) {
        // console.log(res);
        if (res.code == '1') {
          var bjzs = 0;
          for (var i = 0; i < res.data.length; i++) {
            var element = res.data[i];
            bjzs += element.count
          }
          $('.bjzs').text(bjzs)
        }
      }
    })

  }

  // 常用服务--3个便民服务展示 
  // $.ajax({
  //   url: "/web/bmfw/bmfw_item/localItemList.jspc",
  //   data: {
  //     "region_code": sessionStorage.getItem('p_region_code') || '420000000000',
  //     "currentPage": '1',
  //     "pageSize": "4"
  //   },
  //   type: 'post',
  //   dataType: "json",
  //   ContentType: "application/x-www-form-urlencoded",
  //   success: function (res) {
  //     //   console.log('便民服务', res);
  //     if (res.code == 1) {

  //       var gaokaohasFlag = true;
  //       for (var j = 0; j < res.data.records.length; j++) {
  //         var recordsList = res.data.records[j];
  //         if (recordsList.bmfwname == '2021高考成绩查询') {
  //           gaokaohasFlag = false;
  //           break;
  //         }
  //       }

  //       if (gaokaohasFlag) {
  //         var bmfwListData = res.data.records.slice(0, 3)
  //       } else {
  //         var bmfwListData = res.data.records.slice(0, 4)
  //       }




  //       var bmfwListDatahtml = ""
  //       for (var i = 0; i < bmfwListData.length; i++) {
  //         var element = bmfwListData[i];

  //         if (element.bmfwname != '2021高考成绩查询') {
  //           if (element.urlType == '2') {
  //             bmfwListDatahtml += '<li><a class="bmfwType" data-clickId="' + element.bmfwid + '" target="_blank" rel="noopener noreferrer" href="' + element.checkpageurl + '" title="' + element.bmfwname + '">' + element.bmfwname + '</li>'
  //           } else {
  //             bmfwListDatahtml += '<li><a class="bmfwType" data-clickId="' + element.bmfwid + '" target="_blank" rel="noopener noreferrer" href="/webview/bmfw/bmfw_check.html?bmfwId=' + element.bmfwid + '" title="' + element.bmfwname + '">' + element.bmfwname + '</li>'
  //           }
  //         }
  //       }
  //       $('.rmbmfwList').html(bmfwListDatahtml)
  //     }
  //   }
  // })

  // 常用服务--3个热门事项展示 使用部门列表接口
  // $.ajax({
  //   url: "/web/bszn/item_project_transaction_sy",
  //   type: "POST",
  //   dataType: "json",
  //   data: {
  //     "orgCode": "",
  //     "regionCode": sessionStorage.getItem('p_region_code') || '420000000000',
  //     "areaGrade": sessionStorage.getItem('p_region_grade') || '2',
  //     "count": '3',
  //     "isOnline": '1',
  //   },
  //   success: function (data) {
  //     // console.log(data);
  //     if (data.code == "1") {
  //       var rmsxListHtml = ''
  //       for (var i = 0; i < data.data.length; i++) {
  //         var element = data.data[i];
  //         rmsxListHtml += '<li><a target="_blank" rel="noopener noreferrer" href="/webview/bszn/bsznpage.html?transactCode=' + element.TRANSACTCODE + '" title="' + element.TRANSACTNAME + '">' + element.TRANSACTNAME + '</li>'
  //       }
  //       $('.rmsxList').html(rmsxListHtml)
  //     }
  //   }
  // })


  // 服务清单
  getfwqdList()

  function getfwqdList() {
    //获取区划显示对应清单
    var regionCodes = sessionStorage.getItem('p_region_code')||"420000000000";
    //获取区划等级
    var grades = sessionStorage.getItem('p_region_grade')
    //  取前六位区级且只到区级 
    // var pdCode = regionCodes.slice(0, 6) + "000000"

    // console.log(regionCodes, 'regionCodes')
    // console.log(pdCode, 'pdCode')
    if (grades < 5) {
      let fwqdDataList = [
        {
          "itemListType": null,
          "itemType": "2",
          "orderSort": 1,
          "otherCity": null,
          "otherProvince": null,
          "updateTime": "2020-12-10 14:11:17",
          "regionCode": "420000000000",
          "createBy": "system",
          "updateBy": "system",
          "createTime": "2020-12-10 14:11:17",
          "linkUrl": "/webview/zwgk/qzqd.html",
          "name": "权力清单",
          "id": "e69d6de1e1fdce43cce8a32e1c6c10a9",
          "remarks": null,
          "isTrans": "0",
          "status": "1"
        },
        {
          "itemListType": null,
          "itemType": "2",
          "orderSort": 2,
          "otherCity": null,
          "otherProvince": null,
          "updateTime": "2020-12-10 14:11:17",
          "regionCode": "420000000000",
          "createBy": "system",
          "updateBy": "system",
          "createTime": "2020-12-10 14:11:17",
          "linkUrl": "/webview/zwgk/ggfwqd.html",
          "name": "公共服务清单",
          "id": "7db8b3a28f5b8843d58bbfb8848c827d",
          "remarks": null,
          "isTrans": "0",
          "status": "1"
        },
        {
          "itemListType": null,
          "itemType": "2",
          "orderSort": 3,
          "otherCity": null,
          "otherProvince": null,
          "updateTime": "2020-12-10 14:11:17",
          "regionCode": "420000000000",
          "createBy": "system",
          "updateBy": "system",
          "createTime": "2020-12-10 14:11:17",
          "linkUrl": "/webview/zwgk/zjfwqd.html",
          "name": "中介服务清单",
          "id": "abdd5035da90ed43eedb385d1bf54132",
          "remarks": null,
          "isTrans": "0",
          "status": "1"
        },
        {
          "itemListType": null,
          "itemType": "2",
          "orderSort": 4,
          "otherCity": null,
          "otherProvince": null,
          "updateTime": "2020-12-10 14:11:17",
          "regionCode": "420000000000",
          "createBy": "system",
          "updateBy": "system",
          "createTime": "2020-12-10 14:11:17",
          "linkUrl": "/webview/zwgk/SFGPListing.html?type=SF",
          "name": "收费清单",
          "id": "2520d3d2044ee042f4085d2095e85590",
          "remarks": null,
          "isTrans": "0",
          "status": "1"
        },
        {
          "itemListType": null,
          "itemType": "2",
          "orderSort": 5,
          "otherCity": null,
          "otherProvince": null,
          "updateTime": "2020-12-10 14:11:17",
          "regionCode": "420000000000",
          "createBy": "system",
          "updateBy": "system",
          "createTime": "2020-12-10 14:11:17",
          "linkUrl": "/webview/zwgk/pdqd.html",
          "name": "跑动次数清单",
          "id": "4287faf8a2b10a437fa84daa3cc60ec1",
          "remarks": null,
          "isTrans": "0",
          "status": "1"
        },
        {
          "itemListType": null,
          "itemType": "2",
          "orderSort": 6,
          "otherCity": null,
          "otherProvince": null,
          "updateTime": "2020-12-10 14:11:17",
          "regionCode": "420000000000",
          "createBy": "system",
          "updateBy": "system",
          "createTime": "2020-12-10 14:11:17",
          "linkUrl": "/webview/zwgk/tbsx.html",
          "name": "湖北省全省通办事项清单（省级）",
          "id": "9aa04a0e2ad9c2490a2ad302ded79bfa",
          "remarks": null,
          "isTrans": "0",
          "status": "1"
        },
        {
          "itemListType": null,
          "itemType": "2",
          "orderSort": 7,
          "otherCity": null,
          "otherProvince": null,
          "updateTime": "2020-12-10 14:11:17",
          "regionCode": "420000000000",
          "createBy": "system",
          "updateBy": "system",
          "createTime": "2020-12-10 14:11:17",
          "linkUrl": "/webview/zwgk/tbsx.html?type=4",
          "name": "湖北省全省通办事项清单（市州级）",
          "id": "fff1881be2b47e40e4eaaefefb18b925",
          "remarks": null,
          "isTrans": "0",
          "status": "1"
        },
        {
          "itemListType": null,
          "itemType": "2",
          "orderSort": 8,
          "otherCity": null,
          "otherProvince": null,
          "updateTime": "2020-12-10 14:11:17",
          "regionCode": "420000000000",
          "createBy": "system",
          "updateBy": "system",
          "createTime": "2020-12-10 14:11:17",
          "linkUrl": "/webview/zwgk/tbsx.html?type=5",
          "name": "湖北省全省通办事项清单（区县级）",
          "id": "e14d660e8f9dc84d048b96f87d3ac2ba",
          "remarks": null,
          "isTrans": "0",
          "status": "1"
        },
        {
          "itemListType": null,
          "itemType": "2",
          "orderSort": 9,
          "otherCity": null,
          "otherProvince": null,
          "updateTime": "2020-12-10 14:11:17",
          "regionCode": "420000000000",
          "createBy": "system",
          "updateBy": "system",
          "createTime": "2020-12-10 14:11:17",
          "linkUrl": "/webview/zwgk/zmsxblqd.html",
          "name": "证明事项保留清单",
          "id": "004df6306f5c46460268dca65c3b0474",
          "remarks": null,
          "isTrans": "0",
          "status": "1"
        },
        {
          "itemListType": null,
          "itemType": "2",
          "orderSort": 10,
          "otherCity": null,
          "otherProvince": null,
          "updateTime": "2020-12-10 14:11:17",
          "regionCode": "420000000000",
          "createBy": "system",
          "updateBy": "system",
          "createTime": "2020-12-10 14:11:17",
          "linkUrl": "/webview/zwgk/zmsxqxqd.html",
          "name": "证明事项取消清单",
          "id": "2d02a2af81b2984bfb8835086fe91985",
          "remarks": null,
          "isTrans": "0",
          "status": "1"
        }
      ]

      //发送请求获取新数据
      // $.ajax({
      //   // url: '/web/bszn/query/subject/page',
      //   url: '/web/bszn/zwgk/action/list', //df  2021.3.3更换新接口
      //   data: {
      //     // "current": "1",
      //     // "size": "200",
      //     // "itemLisType": "A009",
      //     "regionCode": pdCode
      //   },
      //   type: 'get',
      //   crossDomain: true,
      //   dataType: 'json',
      //   success: function (res) {
      //     // console.log(res, '77777')
      //     if (res.code == 1) {
      //       if (res.data.length > 0) {
      $('#fuqdList').html("")
      var rows = fwqdDataList;
      // 将服务清单跨省通办事项排在最后
      var y = 0; //定义y用于控制循环结束
      for (var i = 0; y < rows.length; y++) {
        if (rows[i].isTrans == "1") {
          rows.push(rows.splice(i, 1)[0]);
        } else {
          i++;
        };
      };
      var html = '';
      for (var i = 0; i < rows.length; i++) {
        html += "<li>"
        if (rows[i].name == "权力清单") {
          html += '<a title="' + rows[i].name + '" href="' + rows[i].linkUrl + '"><img src="/images/indexImg/icon-qlqd.png" width="32" alt="">' + rows[i].name + '</a>'
        } else if (rows[i].name == "公共服务清单") {
          html += '<a title="' + rows[i].name + '" href="' + rows[i].linkUrl + '"><img src="/images/indexImg/icon-ggfwqd.png" width="32" alt="">' + rows[i].name + '</a>'
        } else if (rows[i].name == "中介服务清单") {
          html += '<a title="' + rows[i].name + '" href="' + rows[i].linkUrl + '"><img src="/images/indexImg/icon-zjfwqd.png" width="32" alt="">' + rows[i].name + '</a>'
        } else if (rows[i].name == "收费清单") {
          html += '<a title="' + rows[i].name + '" href="' + rows[i].linkUrl + '"><img src="/images/indexImg/icon-sfqd.png" width="32" alt="">' + rows[i].name + '</a>'
        } else if (rows[i].name == "跑动次数清单") {
          html += '<a title="' + rows[i].name + '" href="' + rows[i].linkUrl + '"><img src="/images/indexImg/icon-pdcsqd.png" width="32" alt="">' + rows[i].name + '</a>'
        } else {
          html += '<a title="' + rows[i].name + '" href="' + rows[i].linkUrl + '"><img src="/images/indexImg/icon-zmsxqd.png" width="32" alt="">' + rows[i].name + '</a>'
        }
        html += "</li>"
      }
      $('#fuqdList').html(html)
      //       }
      //     }
      //   }
      // })

    } else {
      //使用默认数据

    }
  }


  //  导航栏滑动效果
  $('.line_x').each(function (i, v) {
    var lineWidth = $(v).siblings('.active').width() - 20;
    $(v).width(lineWidth)
    $(v).css('left', '10px')
  })

  $('.cen_top_title_item_x').hover(lineHover, lineLeave)
  $('#andy-nav li').hover(lineHover, lineLeave)


  //  2023.4.23 修改菜单选中样式  df
  function lineHover() {
    var lineWidth = $(this).width();
    $(this).siblings('.line_x').width(lineWidth)

    var firstLeft = $(this).parent().find('li').eq(0).offset().left - 10

    var left = $(this).offset().left - firstLeft;
    $(this).siblings('.line_x').stop().animate({
      "left": left
    }, 300);
  }

  function lineLeave() {
    if (!$(this).hasClass('active')) {
      var lineWidth = $(this).siblings('.active').width();
      $(this).siblings('.line_x').width(lineWidth)
      var firstLeft = $(this).parent().find('li').eq(0).offset().left - 10;
      var left = '';
      if ($(this).siblings(".active").offset()) {
        left = $(this).siblings('.active').offset().left - firstLeft;
      }

      $(this).siblings('.line_x').stop().animate({
        "left": left
      }, 300);
    }
  }

})


// // 关闭浏览器，清除相关标识
// $(function () {
//     var beginTime = 0; //执行onbeforeunload的开始时间
//     var differTime = 0; //时间差
//     window.onunload = function () {
//         differTime = new Date().getTime() - beginTime;
//         if (differTime <= 5) {
//             console.log("浏览器关闭");
//             // 关闭浏览器，清除便民和办事扫脸认证标识
//             localStorage.removeItem("bmAndGuidePass");
//             localStorage.removeItem("bmAndGuidePassTimeStamp");
//             // 关闭浏览器，清空用户空间扫脸认证标识
//             localStorage.removeItem("grkjAuthenPass");
//             localStorage.removeItem("grkjAuthenPassTimeStamp");
//         } else {
//             console.log("浏览器刷新");
//         }
//     };
//     window.onbeforeunload = function () {
//         beginTime = new Date().getTime();
//     };
// });

$('.ss_city').click(function () {
  //   console.log('123')
  $('.ss_city_box').toggle().parent('.special_service').css({
    'overflow': 'visible'
  });
  if ($(window).width() < 1025) {
    $('.ssbox').css({
      'height': '77px'
    });
    $('.special_list').css({
      'overflow': 'hidden'
    })
  }

})

$('.manR').click(function () {
  toGrkjUrl(true)
})


if ($(window).width() > 1025) {
  $(".special_service").hover(function (e) {
    $(this).css({
      'height': '124px',
      'overflow': 'visible'
    });
    $('.special_list').css({
      'height': '124px'
    });
  });


  $(".special_service").mouseleave(function (e) {
    e.stopPropagation()
    $(this).css({
      'height': '77px'
    });
    $('.special_list').css({
      'height': '77px'
    });
    $(".special_list").css({
      'overflow': 'hidden'
    });
    // $(".ss_city_box").hide();
  });

} else {
  $(".special_service").hover(function (e) {

  })
}




$(".ss_city_box").mouseleave(function (e) {
  e.stopPropagation()
  // $(this).css({ 'overflow': 'hidden' });
  $('.special_service').css({
    'height': '77px'
  });
  $(".special_service").css({
    'overflow': 'hidden'
  });
  $('.special_list').css({
    'height': '77px'
  });
  $(".special_list").css({
    'overflow': 'hidden'
  });
  $(".ss_city_box").hide();
});



window.onload = function () {
  var gr_int = "";
  var fr_int = "";
  //  type  1便民   0事项
  var interested_service_gr = [
  // {
  //   name: "全省公积金网点查询",
  //   url: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
  //   type: "1",
  //   islogin: "0",
  // },
  {
    name: "医保专区",
    url: "/webview/bmfw/model/hb-ybzq/index.html",
    type: "1",
    islogin: "0",
  },
  {
    name: "湖北婚姻预约登记",
    url: "/webview/bmfw/bmfw_check.html?bmfwId=202105120001&region_code=420000000000",
    type: "1",
    islogin: "1",
  },
  // {
  //   name: "中职毕业证查询",
  //   url: "/webview/bmfw/bmfw_check.html?bmfwId=20201133",
  //   type: "1",
  //   islogin: "0",
  // },
  {
    name: "企业职工社保证明验证",
    url: "https://hbsb.hb12333.com/hbrswt/template/dzsbzmyz.html#/",
    type: "1",
    islogin: "0",
  },
  {
    name: "高级专业技术职务任职资格申报",
    url: "E9D0ED3BE257A19F0ABA3AC9C1559674",
    type: "0",
    islogin: "0",
  },
  // {
  //   name: "机关事业单位养老保险信息查询打印（退休人员待遇信息查询打印）",
  //   url: "3CBDD4B826E9B1140A53ECC7BAB5B0DA",
  //   type: "0",
  //   islogin: "0",
  // },
  // {
  //   name: "机关事业单位养老保险个人权益记录（个人参保证明）",
  //   url: "A4DFE94FED158732DAF7C8C834183891",
  //   type: "0",
  //   islogin: "0",
  // },
  {
    name: "网上公安",
    url: "https://wsgaj.chutianyun.gov.cn//#/",
    type: "1",
    islogin: "0",
  },
  {
    name: "职业技能培训信息管理系统",
    url: "https://www.hbjnpxgl.com/#/manage",
    type: "1",
    islogin: "0",
  },
  ];
  var interested_service_fr = [
  {
    name: "企业政策支持、信息咨询",
    url: "http://sqsl.hbsme.com.cn/sqsl/",
    type: "1",
    islogin: "0",
  },
  {
    name: "安全生产许可证查询",
    url: "/webview/bmfw/bmfw_check.html?bmfwId=B1204",
    type: "1",
    islogin: "0",
  },
  {
    name: "建筑施工企业主要负责人、项目负责人、专职安全生产管理人员新取证申请",
    url: "9FCEC0AF3776C483056578910FC51F5E",
    type: "0",
    islogin: "0",
  },
  {
    name: "机关事业单位参保证明查询打印（单位缴费明细认定）",
    url: "19C8EECA806BEBEA0549114533A24444",
    type: "0",
    islogin: "0",
  },
  {
    name: "建筑施工特种作业人员新取证申请",
    url: "F3323C96BF839DC380016B367C66EAF5",
    type: "0",
    islogin: "0",
  },
  {
    name: "超重超限运输车辆行驶公路许可(高速公路)",
    url: "62D136F52AAA47D526748AD04C6347AC",
    type: "0",
    islogin: "0",
  },
  ];

  // 注释用户信息接口多次调用问题，2023.2.27 df
  // $.ajax({
  // 	url: '/web/user/getUserOnlineInfo.jspc?r=' + Math.random(),
  // 	data: {},
  // 	type: 'post',
  // 	crossDomain: true,
  // 	//async:false,
  // 	dataType: 'json',
  // 	success: function (data) {
  // if (data.code == "1" && data.data.uias_userid != null && data.data.uias_userid != "") {
  if (uias_userid != null && uias_userid != "") {
    console.log("已登录");
    $.ajax({
      url: "/web/user/member/my_zbj_pagelist.jspc",
      data: {},
      type: "post",
      crossDomain: true,
      //async:false,
      dataType: "json",
      success: function (data) {
        // console.log(data);
        if (data.code == 1) {
          $(".bsnumm").text(data.data.total);
        }
      },
      error: function (e) { },
    });
    $.ajax({
      url: "/web/user/dzzz/ezt/getAertificateAllByBszn.jspc",
      data: {},
      type: "post",
      crossDomain: true,
      //async:false,
      dataType: "json",
      success: function (data) {
        // console.log(data);
        if (data.code == 1) {
          //   console.log(data.data);
          if (data.data) {
            $(".zznum").text(data.data);
          } else {
            $(".zznum").text('0');
          }

        }
      },
      error: function (e) { },
    });

    if (window.usertype == "1") {
      //个人
      for (var i = 0; i < interested_service_gr.length; i++) {
        gr_int +=
          '<div url="' +
          interested_service_gr[i].url +
          '" data-islogin="' +
          interested_service_gr[i].islogin +
          '" type="' +
          interested_service_gr[i].type +
          '" title="' +
          interested_service_gr[i].name +
          '" class="list_item"><span>·</span><span class="servicename">' +
          interested_service_gr[i].name +
          "</span></div>";
      }
      $(".service_list").html(gr_int);
    } else if (window.usertype == "2") {
      //企业
      for (var i = 0; i < interested_service_fr.length; i++) {
        fr_int +=
          '<div  url="' +
          interested_service_fr[i].url +
          '" data-islogin="' +
          interested_service_fr[i].islogin +
          '"  type="' +
          interested_service_fr[i].type +
          '" title="' +
          interested_service_gr[i].name +
          '" class="list_item "><span>·</span><span class="servicename">' +
          interested_service_fr[i].name +
          "</span></div>";
      }
      $(".service_list").html(fr_int);
    }
  } else {
    // console.log("未登录");

    for (var i = 0; i < interested_service_gr.length; i++) {
      gr_int +=
        '<div url="' +
        interested_service_gr[i].url +
        '" data-islogin="' +
        interested_service_gr[i].islogin +
        '" type="' +
        interested_service_gr[i].type +
        '" title="' +
        interested_service_gr[i].name +
        '" class="list_item"><span>·</span><span class="servicename">' +
        interested_service_gr[i].name +
        "</span></div>";
    }
    $(".service_list").html(gr_int);
  }
  // },
  // error: function (e) { }
  // });

  //   console.log(window.uias_userid);

  // 猜你感兴趣跳转
  $(".list_item").click(function () {
    //  console.log("123");
    // window.open($(this).attr('url'))
    // $(".zgc").show();
    var openUrl = $(this).attr("url");
    searchSelectData.transactNameBase64 = $(this).attr("url");
    searchSelectData.regionCode = sessionStorage.getItem("p_region_code");
    searchSelectData.regionName = sessionStorage.getItem("p_region_name");
    searchSelectData.areaGrade = sessionStorage.getItem("p_region_grade");
    if ($(this).attr("type") == 1) {
      var isLogin = $(this).attr("data-isLogin");
      if (isLogin == "1") {
        if (checkLogin(true, openUrl, true)) {
          window.open(openUrl);
        }
      } else {
        window.open(openUrl);
      }
    } else {
      // showRegionList(searchSelectData)
      // $('.areaNavBtn_2').addClass('no_select');

      // $('.areaNavBtn_2').text('查看办事指南');
      // $('.area_nav_2').find('.region_x_2').eq(0).addClass('no_select')

      $.ajax({
        url: "/web/bszn/region/getParentRegions.jspc",
        data: {
          p_region_code: searchSelectData.regionCode,
        },
        type: "post",
        crossDomain: true,
        dataType: "json",
        success: function (data) {
          //   console.log(data, "data1");
          //   console.log(
          //     searchSelectData.regionCode,
          //     "searchSelectData.regionCode"
          //   );
          if (data.status != 200) {
            return;
          }
          $(".area_nav_2").html("");
          var htmlxx = "";
          for (var i = data.data.length - 1; i >= 0; i--) {
            var element = data.data[i];

            htmlxx +=
              '<div class="region_item"><a href="javascript:;" class="region_x region_x_2 no_select" data-region="' +
              element.code +
              '" data-grade="' +
              element.grade +
              '" data-name="' +
              element.name +
              '">' +
              (element.name == "湖北省" ?
                element.name + "(省本级)" :
                element.name) +
              "</a></div>";
          }
          $(".area_nav_2").html(htmlxx);
          var areaNum = $(".area_nav_2").find(".region_item").length - 1;
          $(".zgc_x").show();
          $("body").addClass("show_x");
          $(".zgc_model_2").show().siblings().hide();
          $(".area_nav_2").find(".region_x_2").eq(areaNum).click();
        },
        error: function () {
          layer.msg("网络超时请重试", {
            icon: 5,
          });
        },
      });
    }
  });
  // 个人服务/法人服务里面事项跳转;
  // $(".newGrFr_middle").on("click", ".item-service", function () {
  //   searchSelectData.transactNameBase64 = $(this).attr("data-id");
  //   searchSelectData.regionCode = sessionStorage.getItem("p_region_code");
  //   searchSelectData.regionName = sessionStorage.getItem("p_region_name");
  //   searchSelectData.areaGrade = sessionStorage.getItem("p_region_grade");
  //   if ($(this).attr("data-id")) {

  //     $.ajax({
  //       url: "/web/bszn/region/getParentRegions.jspc",
  //       data: {
  //         p_region_code: searchSelectData.regionCode,
  //       },
  //       type: "post",
  //       crossDomain: true,
  //       dataType: "json",
  //       success: function (data) {
  //         //   console.log(data, "data1");
  //         //   console.log(
  //         //     searchSelectData.regionCode,
  //         //     "searchSelectData.regionCode"
  //         //   );
  //         if (data.status != 200) {
  //           return;
  //         }
  //         $(".area_nav_GrFr_2").html("");
  //         var htmlxx = "";
  //         for (var i = data.data.length - 1; i >= 0; i--) {
  //           var element = data.data[i];

  //           htmlxx +=
  //             '<div class="region_item_GrFr"><a href="javascript:;" class="region_x_GrFr region_x_GrFr_2 no_select" data-region="' +
  //             element.code +
  //             '" data-grade="' +
  //             element.grade +
  //             '" data-name="' +
  //             element.name +
  //             '">' +
  //             (element.name == "湖北省"
  //               ? element.name + "(省本级)"
  //               : element.name) +
  //             "</a></div>";
  //         }
  //         $(".area_nav_GrFr_2").html(htmlxx);
  //         var areaNum = $(".area_nav_GrFr_2").find(".region_item_GrFr").length - 1;
  //         $(".zgc_x_GrFr").show();
  //         $("body").addClass("show_x");
  //         $(".zgc_model_GrFr_2").show().siblings().hide();
  //         $(".area_nav_GrFr_2").find(".region_x_GrFr_2").eq(areaNum).click();
  //       },
  //       error: function () {
  //         layer.msg("网络超时请重试", {
  //           icon: 5,
  //         });
  //       },
  //     });
  //   } else {
  //     var code = $(this).attr('data-code');
  //     var url = '/webview/bszn/bsznpage.html?transactCode=' + code + '&taskType=01'

  //     window.open(url)
  //   }
  // });

  $(".whSwiper .ztlb_text").click(function () {
    window.open($(this).attr("data-url"));
  });
}

$(function () {
  // sessionStorage.clear();
  FastClick.attach(document.body);

  var completeRegionCode =
    sessionStorage.getItem("p_region_code") || "420000000000";

  if (completeRegionCode == "420000000000") {
    $("#latelySearhList li a").css({
      color: "#003365"
    });
    $(".andy-search-other .title, .andy-search-other .title1").css({
      color: "#000000",
    });
    $(".index_ehb span").css({
      color: "#003365"
    });
  } else {
    $(".index_ehb span").css({
      color: "#fff"
    });
    $("#latelySearhList li a").css({
      color: "#fff"
    });
    $(".andy-search-other .title, .andy-search-other .title1").css({
      color: "#fff",
    });
  }

  if (regionCode_x.substr(0, 4) == "4201") {
    $(".yqzq_index").attr("href", "/webview/whWeb/whyqzq.html");
    // 武汉一事联办更新地址
    $(".yslb_a").attr("href", "/shell_pc/oneThingSpecialColumn/provinceTheme/localSpecialThemeList?region=420100000000");
    $("#yslb_wh").attr("href", "/shell_pc/oneThingSpecialColumn/provinceTheme/localSpecialThemeList?region=420100000000");
    // $(".yslb_a").attr("href", "http://zwfw.hubei.gov.cn/shell_pc/oneThingSpecialColumn/provinceTheme/localSpecialThemeList?region=420100000000");
    // $("#yslb_wh").attr("href", "http://zwfw.hubei.gov.cn/shell_pc/oneThingSpecialColumn/provinceTheme/localSpecialThemeList?region=420100000000");
  } else {
    $(".yqzq_index").attr("href", "/webview/yqzq/index.html");
    $(".yslb_a").attr("href", "/shell_pc/oneThingSpecialColumn/provinceTheme");
    $("#yslb_wh").attr("href", "/shell_pc/oneThingSpecialColumn/provinceTheme");
  }

  var regionCodes = sessionStorage.getItem("p_region_code")||"420000000000";
  // var pdCode = regionCodes.slice(0, 4);
  var grades = sessionStorage.getItem("p_region_grade");

  if (grades > 3) {
    $(".tymlqd").hide();
  }

  if (completeRegionCode.substr(0, 4) == "4201") {
    $(".whSwiper").remove();
    // $(".qsSwiper").remove();
    // completeRegionCode = completeRegionCode.substr(0, 6) + "000000";
    // for (var i = 0; i < whYslbData.length; i++) {
    //   var element = whYslbData[i];
    //   if (element.regionCode == completeRegionCode) {
    //     // console.log(element);
    //     for (var m = 0; m < element.regionData.length; m++) {
    //       var item = element.regionData[m];
    //       $(".whSwiper")
    //         .find(".yslbName")
    //         .eq(m)
    //         .attr("data-title", item.serverName)
    //         .text(item.serverName);
    //     }
    //   }
    // }
  } else {
    $(".whSwiper").remove();
  }

  if (completeRegionCode != "421100000000") {
    $(".hgzq").remove();
  }

  $(".yyyz").remove();
  if (completeRegionCode == "420700000000") {
    $("#swiper_zq .swiper-wrapper").prepend(
      '<div class="swiper-slide yyyz"><a href="http://zwfw.hubei.gov.cn/shell_pc/tourist/oneCertificatePerIndustry" target="blank" class="left"><h4>"一业一证"服务专区</h4><p>聚焦"高效办成一件事"，持续优化营商环境</p><img src="/images/index/img-yyyz.png" alt=""></a></div>'
    );
    // $('#swiper_zq .swiper-wrapper').prepend('<div class="swiper-slide yyyz"><a href="http://zwfw.hubei.gov.cn:8016/shell_pc/tourist/oneCertificatePerIndustry" target="blank" class="left"><h4>"一业一证"服务专区</h4><p>聚焦"高效办成一件事"，持续优化营商环境</p><img src="/images/index/img-yyyz.png" alt=""></a></div>');
  }

// 蔡伟说只有一张不轮播 df 2025.7.7
  // // 轮播图的切换
  var mySwiper = new Swiper(".swiperBox", {
    // direction: 'vertical', // 垂直切换选项
    loop: true, // 循环模式选项
    // autoplay:4000,
    // 如果需要分页器
    pagination: {
      el: "#tszq-pagination",
      pagination: "#tszq-pagination",
      paginationClickable: "#tszq-pagination",
      clickable: true,
    },
    // 如果需要前进后退按钮
    navigation: {
      nextEl: "#tszqSwiper-next",
      prevEl: "#tszqSwiper-prev",
    },

    // 延时的时间
    autoplay: {
      delay: 4000,
      disableOnInteraction: false,
    },
  });

  // 特色服务的数据
  var list_yyyz = {};
  var yyyzurl = '';
  var hrefUrl = window.location.href;
  // if (hrefUrl.indexOf('8016') > -1 || hrefUrl.indexOf('85') > -1) {
  //   // yyyzurl = '/webview/yyyz/index.html'
  // yyyzurl = "/shell_pc/yyyz";
  // } else {
  yyyzurl = '/shell_pc/oneBusinessOneCertificate'
  // yyyzurl = ' /webview/maintenance/one-industry-one-certificate/index.html'
  // }

  if (sessionStorage.getItem("p_region_code") == '420700000000') {
    // list_yyyz = {
    //   title: "一业一证",
    //   hot: false,
    //   content: "一单告知、一表申请、一口受理、一证准营、一码亮证，聚焦“高效办成一件事”，持续优化营商环境",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/yyyz_new.png",
    //   url: yyyzurl,
    // }
    // list_yyyz = {
    //   title: "圈内通办专区",
    //   hot: false,
    //   new: true,
    //   content: "解决企业群众异地办事“多地跑”、“往返跑”难题",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/sntb_2024_new.png",
    //   url: "/webview/sntb/index.html",
    //   serviceType: "1",//1:链接   2：id专区
    // }
    list_yyyz = {
      title: "全省通办专区",
      hot: false,
      new: true,
      content: '加快推动“最多跑一次”和“就近能办”改革，推行全省通办服务',
      serviceNum: '127项服务',
      imgurl: '/images/newIndex/index_tszq/sntb_new.png',
      url: '/webview/tszq/web/qstb/index.html',
      serviceType:"1",//1:链接   2:id专区
      isLogin:false
    }
  } else {
    // list_yyyz = {
    //   title: "人才服务专区",
    //   hot: false,
    //   content: "享受“一站式”人才服务便捷办理",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/rcfw_new.png",
    //   url: "/webview/rczq/index.html",
    // }
    // list_yyyz = {
    //   title: "圈内通办专区",
    //   hot: false,
    //   new: true,
    //   content: "解决企业群众异地办事“多地跑”、“往返跑”难题",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/sntb_2024_new.png",
    //   url: "/webview/sntb/index.html",
    //   serviceType: "1",//1:链接   2：id专区
    // }
    // list_yyyz = {
    //   title: "全省通办专区",
    //   hot: false,
    //   new: true,
    //   content: '加快推动“最多跑一次”和“就近能办”改革，推行全省通办服务',
    //   serviceNum: '127项服务',
    //   imgurl: '/images/newIndex/index_tszq/sntb_new.png',
    //   url: '/webview/tszq/web/qstb/index.html',
    //   serviceType:"1",//1:链接   2:id专区
    //   isLogin:false
    // }
    list_yyyz = {
      title: "校友回归服务专区",
      hot: false,
      new: true,
      content: '校友服务驿站，事项办理、校友会等综合服务',
      serviceNum: '127项服务',
      imgurl: '/images/newIndex/index_tszq/pic_xyhg.png',
      url: '/webview/tszq/web/xyhg/index.html',
      serviceType:"1",//1:链接   2:id专区
      isLogin:false
    }
  }

  var tsqzDataList = [
    {
      title: "楚商回乡服务专区",
      hot: false,
      new: true,
      content: "楚商归来 支点崛起",
      serviceNum: "127项服务",
      imgurl: "/images/newIndex/index_tszq/pic_cshx.png",
      url: "/webview/tszq/web/cshxfw/index.html",
      serviceType: "1",//1:链接   2：id专区
    },
    {
      title: '返乡创业政策专区',
      hot: false,
      new: true,
      content: '返乡创业机遇抢先知',
      serviceNum: '127项服务',
      imgurl: '/images/newIndex/index_tszq/pic_fxcy.png',
      url: '/webview/hqskzq/list_fxcy.html',
      serviceType:"1",//1:链接   2：id专区
      isLogin:false
  },
    {
        title: '助企惠企服务专区',
        hot: false,
        new: true,
        content: '惠企助企，暖心服务，与企业同心同行',
        serviceNum: '127项服务',
        imgurl: '/images/newIndex/index_tszq/hqsk_finance.png',
        url: '/webview/hqskzq/index.html',
        serviceType:"1",//1:链接   2：id专区
        isLogin:false
    },
    list_yyyz,
    // {
    //   title: "投资/工程建设项目审批",
    //   hot: false,
    //   new: true,
    //   content: "“投资项目联审平台（联审）”和“工程项目审批改革平台（工改）”",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/gcjs_new.png",
    //   url: "/webview/tzgc/index.html",
    //   serviceType: "1",//1:链接   2：id专区
    // },
    // {
    //     title: '简易事项智能办专区（试点）',
    //     hot: false,
    //     content: '简易事项智能办',
    //     serviceNum: '127项服务',
    //     imgurl: '/images/newIndex/index_tszq/jybzq.png',
    //     url:'/webview/tszq/web/znb/index.html',
    //     // uniqueID:"5a745b138e67e10925a0b285fda01586",
    //     serviceType:"1",//1:链接   2：id专区
    //     isLogin:false
    // },
    // {
    //     title: '高考专区',
    //     hot: false,
    //     new:false,
    //     content: '高考成绩查询、录取结果查询',
    //     serviceNum: '127项服务',
    //     imgurl: '/images/newIndex/index_tszq/gk_new.png',
    //     url: '/webview/gkzqNew/index.html',
    //     serviceType:"1",//1:链接   2：id专区
    //     isLogin:false
    // },
    {
        title: '一业一证',
        hot: false,
        new: false,
        content: '一单告知、一表申请、一口受理、一证准营、一码亮证，聚焦“高效办成一件事”，持续优化营商环境',
        serviceNum: '127项服务',
        imgurl: '/images/newIndex/index_tszq/yyyz_new.png',
        url: yyyzurl,
        serviceType:"1",//1:链接   2：id专区
        isLogin:false
    },
    {
        title: '容缺事项承诺办专区',
        hot: false,
        content: '容缺事项承诺办 ',
        serviceNum: '127项服务',
        imgurl: '/images/newIndex/rqbzq.png',
        url:'/webview/tszq/web/rqbzq/rqbzq.html',
        // uniqueID:"5a745b138e67e10925a0b285fda01586",
        serviceType:"1",//1:链接   2：id专区
        isLogin:false
    },
    {
        title: '政策服务免申办专区（试点）',
        hot: false,
        content: '免申办、惠企服务集成专区',
        serviceNum: '127项服务',
        imgurl: '/images/newIndex/index_tszq/msbzq.png',
        url:'/webview/tszq/web/msb/index.html',
        // uniqueID:"5a745b138e67e10925a0b285fda01586",
        serviceType:"1",//1:链接   2：id专区
        isLogin:false
    },
   
    
    // {
    //     title: "一业一证",
    //     hot: false,
    //     content: "一单告知、一表申请、一口受理、一证准营、一码亮证，聚焦“高效办成一件事”，持续优化营商环境",
    //     serviceNum: "127项服务",
    //     imgurl: "/images/newIndex/index_tszq/yyyz_new.png",
    //     url: yyyzurl,
    //   },
   
    // {
    //   title: "圈内通办专区",
    //   hot: false,
    //   content: "解决企业群众异地办事“多地跑”、“往返跑",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/qntbzq.png",
    //   url: "/webview/sntb/index.html",
    //   serviceType: "1",//1:链接   2：id专区
    // },
    // {
    //   title: "跨省通办",
    //   hot: false,
    //   new: false,
    //   content: "一地认证、全程网办、异地可办、多地联办、就近办理",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/kstb_new.png",
    //   url: "/webview/kstb/kstb.html",
    //   serviceType: "1",//1:链接   2：id专区
    // },
    // {
    //   title: "企业开办登记专区",
    //   hot: false,
    //   new: true,
    //   content: "一次填报、并联审批、证照联办",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/qykb_new.png",
    //   url: "/webview/tszq/web/qykb/index.html",
    //   serviceType: "1",//1:链接   2：id专区
    //   isLogin: true
    // },
    //  {
    //   title: "医保服务专区",
    //   hot: false,
    //   content: "参保单位（个人）、医药机构、药品耗材企业",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/yb_new.png",
    //   url: "/webview/bmfw/model/hb-ybzq/index.html",
    //   serviceType: "1",//1:链接   2：id专区
    // },
    // {
    //   title: "助残服务专区",
    //   // hot:'/images/newIndex/index_tszq/hot_new.png',
    //   hot: false,
    //   new: true,
    //   content:
    //     "弱有所扶、面向残疾人，提供康复、补贴、惠残就业、证件办理、康复辅具",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/zc_new.png",
    //   url: "/webview/zczq/index_2021.html",
    // },
    // {
    //   title: "敬老助老专区",
    //   hot: false,
    //   content: "养老资格认证、老年优待证办理",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/jl_new.png",
    //   url: "/webview/jlalzq/index_2021.html",
    // },
    // {
    //   title: '新冠肺炎疫情防控专区',
    //   hot: false,
    //   new: false,
    //   content: '疫情上报、健康码申领',
    //   serviceNum: '127项服务',
    //   imgurl: '/images/newIndex/index_tszq/yq_new.png',
    //   url: '/webview/yqzq/index.html',
    // }, 
    // {
    //   title: '特色便民专区',
    //   hot: false,
    //   new: true,
    //   content: '融合用水、用电、用气、公证服务、法律援助五类服务入口，便于集中办理',
    //   serviceNum: '127项服务',
    //   imgurl: '/images/newIndex/index_tszq/tsbmzq_img.png',
    //   url: '/webview/tszq/web/fivezqIndex/index.html',
    //   serviceType: "1",//1:链接   2：id专区
    // },
    // {
    //   title: "圈内通办专区",
    //   hot: false,
    //   new: true,
    //   content: "解决企业群众异地办事“多地跑”、“往返跑”难题",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/sntb_2024_new.png",
    //   url: "/webview/sntb/index.html",
    // },
    
    
    // {
    //   title: '智慧投资平台(测试)',
    //   hot: false,
    //   new: true,
    //   content: '“投资项目联审平台（联审）”和“工程项目审批改革平台（工改）”',
    //   serviceNum: '127项服务',
    //   imgurl: '/images/newIndex/index_tszq/gcjs_new.png',
    //   linkUrl: '/webview/tzgc/newIndex.html',
    //   uniqueID:"eef08ffc260badcedd0911e96e2d41ef",
    //   serviceType:"2",//1:链接   2：id专区
    //   isLogin:false
    // }
    // {
    //   title: "人才服务专区",
    //   hot: false,
    //   new: true,
    //   content: "享受“一站式”人才服务便捷办理",
    //   serviceNum: "127项服务",
    //   imgurl: "/images/newIndex/index_tszq/rcfw_new.png",
    //   url: "/webview/rczq/index.html",
    // },
    {
      title: '人才服务专区',
      hot: false,
      content: '享受“一站式”人才服务便捷办理',
      serviceNum: '127项服务',
      imgurl: '/images/newIndex/index_tszq/rcfw_new.png',
      url: '/webview/rczq/index.html',
      serviceType:"1",//1:链接   2：id专区
      isLogin:false
    },
    // {
    //   title: '敬老助老专区',
    //   hot: false,
    //   content: '养老资格认证、老年优待证办理',
    //   serviceNum: '127项服务',
    //   imgurl: '/images/newIndex/index_tszq/jl_new.png',
    //   url: '/webview/jlalzq/index_2021.html',
    //   serviceType:"1",//1:链接   2：id专区
    //   isLogin:false
    // },
  ];
  // 一人一企一档数据
  let list_yryqyd = {};
  let PRegionCode = sessionStorage.getItem("p_region_code")
  if (PRegionCode && PRegionCode.indexOf("4208") != -1) {
    list_yryqyd = {
      title: "一人一企一档（荆门）",
      hot: false,
      new: true,
      content: "企业与个人数字档案、惠民利企场景服务提供一站式平台",
      imgurl: "/images/newIndex/index_tszq/yryqydJM.png",
      url: "/webview/grkj/project/space/#/jingmenindex",
      isLogin: true,
      serviceType: "1",//1:链接   2：id专区
    }
    // tsqzDataList.unshift(list_yryqyd)
    // tsqzDataList.splice(4, 1)
    // 将一人一企一档插入到第二项
    tsqzDataList.splice(1,0,list_yryqyd);
    //删除第5项特色便民服务
    tsqzDataList.splice(5, 1);
  } else if (PRegionCode && PRegionCode.indexOf("4206") != -1) {
    list_yryqyd = {
      title: "一人一企一档（襄阳）",
      hot: false,
      new: true,
      content: "企业与个人数字档案、惠民利企场景服务提供一站式平台",
      imgurl: "/images/newIndex/index_tszq/yryqydJM.png",
      url: "/webview/grkj/project/space/#/indexXyZq",
      isLogin: true,
      serviceType: "1",//1:链接   2：id专区
    }
    // tsqzDataList.unshift(list_yryqyd)
    // tsqzDataList.splice(4, 1)
    // 将一人一企一档插入到第二项
    tsqzDataList.splice(1,0,list_yryqyd);
    //删除第5项特色便民服务
    tsqzDataList.splice(5, 1);
  } else if (PRegionCode && PRegionCode.indexOf("4213") != -1) {
    list_yryqyd = {
      title: "一企一档（随州）",
      hot: false,
      new: true,
      content: "企业与个人数字档案、惠民利企场景服务提供一站式平台",
      imgurl: "/images/newIndex/index_tszq/yryqydJM.png",
      url: "/webview/grkj/project/space/#/suizhouZq",
      isLogin: true,
      serviceType: "1",//1:链接   2：id专区
    }
    // tsqzDataList.unshift(list_yryqyd)
    // tsqzDataList.splice(4, 1)
    // 将一人一企一档插入到第二项
    tsqzDataList.splice(1,0,list_yryqyd);
    //删除第5项特色便民服务
    tsqzDataList.splice(5, 1);
  } else if (PRegionCode && PRegionCode.indexOf("421221") != -1) {
    list_yryqyd = {
      title: "一人一企一档（嘉鱼）",
      hot: false,
      new: true,
      content: "企业与个人数字档案、惠民利企场景服务提供一站式平台",
      imgurl: "/images/newIndex/index_tszq/yryqydJM.png",
      url: "/webview/grkj/project/space/#/jiayuindex",
      isLogin: true,
      serviceType: "1",//1:链接   2：id专区
    }
    // tsqzDataList.unshift(list_yryqyd)
    // tsqzDataList.splice(4, 1)
    // 将一人一企一档插入到第二项
    tsqzDataList.splice(1,0,list_yryqyd);
    //删除第5项特色便民服务
    tsqzDataList.splice(5, 1);
  }else if(PRegionCode && PRegionCode.indexOf("421100000000") != -1) {
    list_yryqyd = {
        title: '“毕办好”增值服务专区（英山）',
        hot: false,
        new: true,
        content: '一网协同、一站办理，为市场主体提供融项目、金融、法治、人才、知识产权等个性化衍生服务。',
        // serviceNum: '127项服务',
        imgurl: '/images/newIndex/index_tszq/bbh.png',
        linkUrl: '/webview/tzgc/newIndex.html',
        uniqueID:"db9d82021878cb2c55c2268e438fdfcb",
        serviceType:"2",//1:链接   2：id专区
        isLogin:false
      }
      // 将一人一企一档插入到第二项
    tsqzDataList.splice(4,0,list_yryqyd);
    //删除第5项特色便民服务
    tsqzDataList.splice(8, 1);
  }else if(PRegionCode && PRegionCode.indexOf("421124000000") != -1) {
    list_yryqyd = {
        title: '“毕办好”增值服务专区（英山）',
        hot: false,
        new: true,
        content: '一网协同、一站办理，为市场主体提供融项目、金融、法治、人才、知识产权等个性化衍生服务。',
        // serviceNum: '127项服务',
        imgurl: '/images/newIndex/index_tszq/bbh.png',
        linkUrl: '/webview/tzgc/newIndex.html',
        uniqueID:"db9d82021878cb2c55c2268e438fdfcb",
        serviceType:"2",//1:链接   2：id专区
        isLogin:false
      }
      // 将一人一企一档插入到第二项
    tsqzDataList.splice(0,0,list_yryqyd);
    //删除第5项特色便民服务
    tsqzDataList.splice(8, 1);
  }
  // console.log(tsqzDataList,'tsqzDataList')
  UlHtml(tsqzDataList);




  // 热门分类的数据
  var hotTypeDateList_gr = [{
    imgurl: "/images/newIndex/index_rmfl/jycy_new.png",
    title: "就业创业",
    child: [{
      name: "档案的接收和转递",
      id: "11F38F1F96E95E6198B0B10B77A1ED93",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "失业登记",
      id: "6EBAEC95D15F1763202EB39AE27E7F6F",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "职业技能鉴定补贴申领",
      id: "5869C4C4D7098BC85371819459CD02C0",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  {
    imgurl: "/images/indexImg/fr1.png",
    title: "企业设立",
    child: [{
      name: "内资公司设立登记",
      id: "D9614BDBE2CC490AAE8AFF3C4AD62CAD",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "内资公司变更登记",
      id: "69C4997F673BD33D2D6E4C95B508B31B",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "内资公司注销登记",
      id: "F7FC86DBA0D2A4587A1F00A94CBD2EBF",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  {
    imgurl: "/images/newIndex/index_rmfl/zfbz_new.png",
    title: "住房保障",
    child: [{
      name: "购买自住住房提取住房公积金",
      id: "6B1B2E73D7E4CC6F0ABC7F7E8967CB16",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "房屋租赁登记备案",
      id: "301A9E51A71B3F6933A33B6E940B970B",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "公租房承租资格确认",
      id: "1A081581A97A39B7EC8A1603466747B1",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  {
    imgurl: "/images/newIndex/index_rmfl/shbz_new.png",
    title: "社会保障",
    child: [{
      name: "社会保障卡服务（申领）",
      id: "FF946F197CBEC3DAACDA0CCB8E9CF3DF",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "城乡居民参保登记",
      id: "2106D04BD9DE99C6327A3106E3DF34B3",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "失业保险金申领",
      id: "36585CCF788734925848ABF712770981",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  {
    imgurl: "/images/newIndex/index_rmfl/zyzg_new.png",
    title: "职业资格",
    child: [{
      name: "教师资格认定",
      id: "",
      transactCode: "11420000011043161T200010501300004",
      type: "0",
      islogin: "0",
    },
    {
      name: "申报职业技能鉴定",
      id: "4E995DBC389409F2B3F68FC411904F4F",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "专业技术人员资格证书办理",
      id: "22F5A70502112E02203AFBEB9C4157E0",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  {
    imgurl: "/images/newIndex/index_rmfl/qtfu_new.png",
    title: "其他",
    child: [{
      name: "名称自主申报（预先登记）",
      id: "E49C5977EBBAB9551A704C8F6CFD8E65",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "残疾人辅助器具适配服务",
      id: "0FDCEDA9801E2409F78341E7BD6C435D",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "劳动者申请立案",
      id: "DE8DD2E5687DFC3AA2CF006CE283BEEA",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  ];

  var hotTypeDateList_fr = [{
    imgurl: "/images/indexImg/fr1.png",
    title: "企业设立",
    child: [{
      name: "内资公司设立登记",
      id: "D9614BDBE2CC490AAE8AFF3C4AD62CAD",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "内资公司变更登记",
      id: "69C4997F673BD33D2D6E4C95B508B31B",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "内资公司注销登记",
      id: "F7FC86DBA0D2A4587A1F00A94CBD2EBF",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  {
    imgurl: "/images/indexImg/fr2.png",
    title: "准营准办",
    child: [{
      name: "网络预约出租汽车驾驶员从业资格证核发",
      id: "0F947FE09CDD8ADB08864FB5A8BF6E64",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "超重超限运输车辆行驶公路许可（跨市州)",
      id: "0D582B22530C7A662FDF2CBC182559AF",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "临时占用公共体育场（馆）设施审批",
      id: "12778BCF8F14D0536696A1565ED4737D",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  {
    imgurl: "/images/indexImg/fr3.png",
    title: "抵押质押",
    child: [{
      name: "抵押权首次登记",
      id: "F8D1C16E831442AC0911DD9E29ED53A0",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "预购商品房抵押预告登记转抵押权首次登记",
      id: "A963E3D0FA24FF225A88E11E9F20B431",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "企业不动产抵押注销登记",
      id: "6F7C987260117C39B5270AACC5B1DD58",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  {
    imgurl: "/images/indexImg/fr4.png",
    title: "行政缴费",
    child: [{
      name: "契税申报",
      id: "6D35152F34B9A61CEC19B4E1812C190A",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "房产交易申报",
      id: "E56009BBB06210CA7C2F85EAB9BF2E44",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "车船税申报",
      id: "7F4236BE9DBA3E6CA0154F59996086C6",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  {
    imgurl: "/images/indexImg/fr5.png",
    title: "社会保障",
    child: [{
      name: "劳动能力复查鉴定申请",
      id: "57628CF1115A2D64008D1B23C2F27411",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "一次性工伤医疗补助金申请",
      id: "CCC0502D108AD26BC6C8A3CF1B182379",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "失业保险金申领",
      id: "36585CCF788734925848ABF712770981",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  {
    imgurl: "/images/indexImg/fr6.png",
    title: "其他",
    child: [{
      name: "二级建造师初始注册",
      id: "9BE3C2B7D772DABE8FE15DE46F626E57",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "技术合同认定登记",
      id: "3D70A243EB538A7CD9C9B35F0BC9984A",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    {
      name: "劳动人事争议仲裁用人单位申请立案",
      id: "AB4EB0215429848CFED7CE5C26322C6D",
      transactCode: "",
      type: "0",
      islogin: "0",
    },
    ],
  },
  ];

  var hotTypeHtml = "";
  for (var i = 0; i < hotTypeDateList_gr.length; i++) {
    var dataitem = hotTypeDateList_gr[i];
    hotTypeHtml += "<li>";
    hotTypeHtml += "<div>";
    hotTypeHtml += '<img src="' + dataitem.imgurl + '" alt="">';
    hotTypeHtml += "</div>";
    hotTypeHtml += "<div>";
    hotTypeHtml += "<h3>" + dataitem.title + "</h3>";

    for (var j = 0; j < dataitem.child.length; j++) {
      var dataitemChild = dataitem.child[j];
      hotTypeHtml +=
        '<p class="item-service" data-code="' +
        dataitemChild.transactCode +
        '" data-id="' +
        dataitemChild.id +
        '"><span class="yuan">·</span>' +
        dataitemChild.name +
        "</p>";
    }

    hotTypeHtml += "</div>";
  }
  $(".hottypeUl").html(hotTypeHtml);
  $(".top_bm_x").hide();
  $(".newGrFr_top").on("click", "h3", function () {
    // console.log($(this).attr("type"));
    $('.gonext').show()
    if ($(this).attr("type") == "gr") {
      $('.top_bm_x').hide()
      $(".hottypeUl").show();
      $(".hotname").text("热门分类");
      $(".gonext").attr("url", "/webview/fw/grfw.html");
      $(".swiper-bmlist .swiper-wrapper").hide();
      var hotTypeHtml = "";
      for (var i = 0; i < hotTypeDateList_gr.length; i++) {
        var dataitem = hotTypeDateList_gr[i];
        hotTypeHtml += "<li>";
        hotTypeHtml += "<div>";
        hotTypeHtml += '<img src="' + dataitem.imgurl + '" alt="">';
        hotTypeHtml += "</div>";
        hotTypeHtml += "<div>";
        hotTypeHtml += "<h3>" + dataitem.title + "</h3>";

        for (var j = 0; j < dataitem.child.length; j++) {
          var dataitemChild = dataitem.child[j];
          hotTypeHtml +=
            '<p class="item-service" data-code="' +
            dataitemChild.transactCode +
            '" data-id="' +
            dataitemChild.id +
            '"><span class="yuan">·</span>' +
            dataitemChild.name +
            "</p>";
        }

        hotTypeHtml += "</div>";
      }
      $(".hottypeUl").html(hotTypeHtml);
    } else if ($(this).attr("type") == "fr") {
      //   console.log("进入法人");
      $(".hottypeUl").show();
      $(".hotname").text("热门分类");
      $('.top_bm_x').hide()
      // $('.gonext').show()
      // $('.hottypeUl').show()

      $(".swiper-bmlist .swiper-wrapper").hide();
      $(".gonext").attr("url", "/webview/fw/frfw.html");
      var hotTypeHtml = "";
      for (var i = 0; i < hotTypeDateList_fr.length; i++) {
        var dataitem = hotTypeDateList_fr[i];
        hotTypeHtml += "<li>";
        hotTypeHtml += "<div>";
        hotTypeHtml += '<img src="' + dataitem.imgurl + '" alt="">';
        hotTypeHtml += "</div>";
        hotTypeHtml += "<div>";
        hotTypeHtml += "<h3>" + dataitem.title + "</h3>";

        for (var j = 0; j < dataitem.child.length; j++) {
          var dataitemChild = dataitem.child[j];
          hotTypeHtml +=
            '<p class="item-service" data-code="' +
            dataitemChild.transactCode +
            '" data-id="' +
            dataitemChild.id +
            '"><span class="yuan">·</span>' +
            dataitemChild.name +
            "</p>";
        }

        hotTypeHtml += "</div>";
      }
      $(".hottypeUl").html(hotTypeHtml);
    } else {
      $(".hotname").text("热门部门");
      $(".hottypeUl").hide();
      $('.gonext').hide()
      $('.top_bm_x').show()
      $(".swiper-bmlist .swiper-wrapper").show();
      $.ajax({
        url: "/web/bszn/dept/findDeptList.jspc",
        dataType: "json",
        type: "POST",
        ContentType: "application/x-www-form-urlencoded",
        data: {
          region_code: sessionStorage.getItem("p_region_code"),
        },
        success: function (res) {
          var bmdata = "";
          bmdata += " <ul class='swiperbmfwUl'>";
          //   console.log(res);
          if (res.code == "1") {
            $("#swiper_bm").find(".loading_x").hide();
            var count = res.data.length;
            var screenWidth = $(window).width(),
              bm_total,
              grfr_total;
            // console.log(screenWidth);
            if (screenWidth > 1440) {
              bm_total = 16;
            } else if (screenWidth <= 1440) {
              bm_total = 15;
            }
            let objNameCode = {
              "420222040400": "𣲗山村委会",
              "420222040000": "𣲗源口镇",
              "420222042100": "𣲗源口村委会"
            }
            var pageTotal_bm = Math.ceil(count / bm_total); // 获取总页数
            for (var i = 0; i < pageTotal_bm; i++) {
              var swiper_slide = document.createElement("div");
              $(swiper_slide).attr("class", "swiper-slide");
              $("#swiper_bm").find(".swiper-wrapper").append(swiper_slide);
            }
            // console.log("123");
            var url_bm = "/webview/bszn/bmsy.html?department=";
            for (var m = 0; m < pageTotal_bm; m++) {
              var slideLiHtml = '<ul class="type_bm clearfix">';
              for (var j = 0; j < res.data.length; j++) {
                var element = res.data[j];
                if (Math.floor(j / bm_total) == m) {
                  let SHORT_NAME = element.SHORT_NAME
                  if (objNameCode[element.REGION_CODE]) SHORT_NAME = objNameCode[element.REGION_CODE]
                  slideLiHtml +=
                    '<li><a target="_blank" rel="noopener noreferrer" href="' +
                    url_bm +
                    element.CODE +
                    '" title="' +
                    element.NAME +
                    '">' +
                    SHORT_NAME +
                    "</a></li>";
                }
              }
              slideLiHtml += "</ul>";
              $("#swiper_bm")
                .find(".swiper-wrapper")
                .find(".swiper-slide")
                .eq(m)
                .html(slideLiHtml);
            }

            // }
            var mySwiper = new Swiper("#swiper_bm", {
              // loop: true, // 循环模式选项
              navigation: {
                nextEl: "#button-next-bm",
                prevEl: "#button-prev-bm",
                disabledClass: "my-button-disabled",
              },
              // 如果需要分页器
              pagination: {
                el: "#pagination_bm",
                clickable: true,
              },
              observer: true,
              observerParents: true,
            });
            mySwiper.el.onmouseover = function () {
              mySwiper.navigation.$nextEl.removeClass("hide");
              mySwiper.navigation.$prevEl.removeClass("hide");
            };
            mySwiper.el.onmouseout = function () {
              mySwiper.navigation.$nextEl.addClass("hide");
              mySwiper.navigation.$prevEl.addClass("hide");
            };
          } else {
            // console.log('获取数据失败')
          }
        },
        error: function () {
          // console.log('获取数据失败')
        },
      });
    }
  });
  $(".gonext").click(function () {
    if ($(this).attr("url").indexOf("grfw.html") != -1) {
      sessionStorage.setItem("active_nav_item", "nav_grfw");
    } else {
      sessionStorage.setItem("active_nav_item", "nav_frfw");
    }
    window.open($(this).attr("url") + "?v=20211029");
  });

  // $('.bmlistt').click(function(){
  //     console.log('点击了')
  //     window.open($(this).attr('url'))
  // })
  $(".Bmfw_content").on("click", "li", function () {
    // console.log("点击了");
    var openUrl = $(this).attr("url");
    var isLogin = $(this).attr("data-isLogin");
    var title = $(this).attr("title");
    let modular = '便民服务'
    if (isLogin == "1") {
      if (checkLogin(true, openUrl, true)) {
        // getNativeIp('',title,openUrl,modular)
        window.open(openUrl);
      }
    } else {
      // getNativeIp('',title,openUrl,modular)
      window.open(openUrl);
    }
    // window.open($(this).attr("url"));
  });
  $(".newGrFr_bottom").on("click", "li", function () {
    // console.log("点击了");
    // window.open($(this).attr('url'))
  });
  // 便民服务的数据
  var customersService = [{
    regionCode: "4200", //湖北省
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "省直企业养老保险待遇查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B010201",
      isLogin: 1,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "个人缴费记录查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280014",
      isLogin: 1,
    },
    {
      itemName: "身份证办理进度查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20201094&region_code=420000000000",
      isLogin: 1,
    },
    {
      itemName: "湖北婚姻预约登记",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202105120001&region_code=420000000000",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010&region_code=420000000000",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4201", //武汉市
    serviceList: [{
      itemName: "养老保险参保凭证",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021659",
      isLogin: 1,
    },
    {
      itemName: "社保缴费证明",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021701",
      isLogin: 1,
    },
    {
      itemName: "失业金人员待遇领取查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021257",
      isLogin: 1,
    },
    {
      itemName: "居住证查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B060301",
      isLogin: 0,
    },
    {
      itemName: "老年人优待证办理",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/420100wh/wh-lnrydzb/index.html",
      isLogin: 1,
    },
    {
      itemName: "公积金个人明细查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021719",
      isLogin: 1,
    },
    {
      itemName: "公积金个人贷款信息查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021720",
      isLogin: 1,
    },
    {
      itemName: "不动产证书限制状态查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021723",
      isLogin: 1,
    },
    ],
  },
  {
    regionCode: "4206", //襄阳市
    serviceList: [{
      itemName: "城镇企业职工社保查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/420600xy/xy-bmfwcx/#/sbIndex",
      isLogin: 1,
    },
    {
      itemName: "襄阳市不动产查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/420600xy/xy-bmfwcx/#/bdc",
      isLogin: 1,
    },
    {
      itemName: "商品房预售许可信息查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/420600xy/xy-bmfwcx2/#/spysxk",
      isLogin: 0,
    },
    {
      itemName: "公积金查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/420600xy/xy-bmfwcx/#/gjjIndex",
      isLogin: 1,
    },
    {
      itemName: "高层次人才住房补贴",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/420600xy/xy-qtzhbl/#/",
      isLogin: 1,
    },
    {
      itemName: "襄阳市退休人员信息",
      itemUrl: "http://zwfw.hubei.gov.cn/webview/bmfw/bmfw_check.html?bmfwId=B0110&region_code=420600000000",
      isLogin: 0,
    },
    {
      itemName: "专业技术人员职称证书查验（中初级）",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/420600xy/xy-bmfwcx/#/zyjsryzczscy",
      isLogin: 1,
    },
    {
      itemName: "单位月台账核定缴费明细表",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/420600xy/xy-bmfwcx/#/dwytzhdjfmx",
      isLogin: 1,
    },
    ],
  },
  {
    regionCode: "4205", //宜昌市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "省直企业养老保险待遇查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B010201",
      isLogin: 1,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "个人缴费记录查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280014",
      isLogin: 1,
    },
    {
      itemName: "身份证办理进度查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20201094&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "湖北婚姻预约登记",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202105120001&region_code=420000000000",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010&region_code=420000000000",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4202", //黄石市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010",
      isLogin: 0,
    },
    {
      itemName: "项目预售许可证信息",
      itemUrl: "/dsbmfw/420200hs/hs-xmysxkzxx/index.html",
      isLogin: 0,
    },
    {
      itemName: "黄石中考成绩",
      itemUrl: "/dsbmfw/420200hs/hs-zkcj/index.html",
      isLogin: 0,
    },
    {
      itemName: "工伤定点医疗机构",
      itemUrl: "/dsbmfw/420200hs/hs-gsddyljgylb/index.html",
      isLogin: 0,
    },
    {
      itemName: "公交充值网点",
      itemUrl: "/dsbmfw/420200hs/hs-gjczwd/index.html",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4203", //十堰市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "省直企业养老保险待遇查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B010201",
      isLogin: 1,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "个人缴费记录查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280014",
      isLogin: 1,
    },
    {
      itemName: "身份证办理进度查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20201094&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "湖北婚姻预约登记",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202105120001&region_code=420000000000",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010&region_code=420000000000",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4210", //荆州市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010",
      isLogin: 0,
    },
    {
      itemName: "学区查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B421009",
      isLogin: 1,
    },
    {
      itemName: "养老机构",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B2020123014",
      isLogin: 1,
    },
    {
      itemName: "公证处查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=110001",
      isLogin: 0,
    },
    {
      itemName: "司法鉴定机构",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20201104",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4208", //荆门市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "不动产登记办理进度查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=2021012805",
      isLogin: 1,
    },
    {
      itemName: "水费查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/420800jm/JmWaterSearch/index.html",
      isLogin: 0,
    },
    {
      itemName: "公积金查询",
      itemUrl: "h/webview/bmfw/bmfw_check.html?bmfwId=20200410120001",
      isLogin: 1,
    },
    {
      itemName: "公积金贷款信息查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20200410120401",
      isLogin: 1,
    },
    {
      itemName: "医保定点药店",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20200410120602",
      isLogin: 1,
    },
    {
      itemName: "小学划片",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B4208044",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4207", //鄂州市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "省直企业养老保险待遇查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B010201",
      isLogin: 1,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "个人缴费记录查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280014",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010",
      isLogin: 0,
    },
    {
      itemName: "鄂州市自助开锁",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B1210",
      isLogin: 0,
    },
    {
      itemName: "自来水用水报装",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=2021030901",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4209", //孝感市
    serviceList: [{
      itemName: "职工参保信息查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021625",
      isLogin: 1,
    },
    {
      itemName: "职工参保缴费信息查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021654",
      isLogin: 1,
    },
    {
      itemName: "公积金查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021616",
      isLogin: 1,
    },
    {
      itemName: "公积金贷款查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20201619",
      isLogin: 1,
    },
    {
      itemName: "房查证明单结果查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=2020123017",
      isLogin: 0,
    },
    {
      itemName: "商品房预售许可查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021622",
      isLogin: 0,
    },
    {
      itemName: "小学学区查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B4209044",
      isLogin: 0,
    },
    {
      itemName: "教师资格认定查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=2020123005",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4211", //黄冈市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "省直企业养老保险待遇查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B010201",
      isLogin: 1,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "个人缴费记录查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280014",
      isLogin: 1,
    },
    {
      itemName: "身份证办理进度查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20201094&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "湖北婚姻预约登记",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202105120001&region_code=420000000000",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010&region_code=420000000000",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4212", //咸宁市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "省直企业养老保险待遇查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B010201",
      isLogin: 1,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "身份证办理进度查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20201094&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "湖北婚姻预约登记",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202105120001&region_code=420000000000",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "咸宁市中考成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040103",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4213", //随州市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "省直企业养老保险待遇查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B010201",
      isLogin: 1,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "个人缴费记录查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280014",
      isLogin: 1,
    },
    {
      itemName: "身份证办理进度查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20201094&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "湖北婚姻预约登记",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202105120001&region_code=420000000000",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010&region_code=420000000000",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "4228", //恩施州
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "湖北婚姻预约登记",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202105120001&region_code=420000000000",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "政务服务大厅查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/422822es/zwfw-zwfwdt/index.html",
      isLogin: 1,
    },
    {
      itemName: "档案信息查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/422822es/ggzp-document/index.html",
      isLogin: 1,
    },
    {
      itemName: "线路车预约",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/422822es/xlcyy/index.html",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "429004", //仙桃市
    serviceList: [{
      itemName: "养老保险缴费信息查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429004xt/xt-ylbxjfxxcx/index.html",
      isLogin: 1,
    },
    {
      itemName: "老年优待证查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429004xt/xt-lnydzcx/index.html",
      isLogin: 1,
    },
    {
      itemName: "公积金信息查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20200210115701",
      isLogin: 1,
    },
    {
      itemName: "公积金贷款信息查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=2020092621",
      isLogin: 1,
    },
    {
      itemName: "不动产交易信息查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429004xt/xt-bdcjyxxcx/index.html",
      isLogin: 0,
    },
    {
      itemName: "商品房预售许可证查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=2020092701",
      isLogin: 1,
    },
    {
      itemName: "残疾人补助信息查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429004xt/xt-cjrbzxxcx/index.html",
      isLogin: 1,
    },
    {
      itemName: "特种作业操作证查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429004xt/xt-tzzyczzcx/index.html",
      isLogin: 1,
    },
    ],
  },
  {
    regionCode: "429006", //天门市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010",
      isLogin: 0,
    },
    {
      itemName: "燃气营业厅信息查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=1450387219174203393",
      isLogin: 1,
    },
    {
      itemName: "水务营业网点信息查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202001021742",
      isLogin: 0,
    },
    {
      itemName: "天门市医保特殊慢性病病种及待遇查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=2021012813",
      isLogin: 1,
    },
    {
      itemName: "天门市医疗保障经办联系方式查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=2021012815",
      isLogin: 0,
    },
    {
      itemName: "天门市基层法律服务所查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=2021012811",
      isLogin: 0,
    },
    ],
  },
  {
    regionCode: "429005", //潜江市
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010&region_code=420000000000",
      isLogin: 0,
    },
    {
      itemName: "不动产登记办理网点",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429005qj/qj_pc_bdcdjblwd/index.html",
      isLogin: 1,
    },
    {
      itemName: "执业药师注册证查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429005qj/qj_pc_zyyszczcx/index.html",
      isLogin: 0,
    },
    {
      itemName: "中小学服务范围划分",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429005qj/qj_pc_zxxfwfwhf/index.html",
      isLogin: 0,
    },
    {
      itemName: "中考成绩查询服务",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429005qj/qj_pc_zkcjcxfw/index.html",
      isLogin: 1,
    },
    {
      itemName: "潜江市法律服务场所信息查询",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429005qj/qj_pc_qjsflfwcsxxcx/index.html",
      isLogin: 1,
    },
    ],
  },
  {
    regionCode: "429021", //神农架林区
    serviceList: [{
      itemName: "全省公积金网点查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B0501",
      isLogin: 0,
    },
    {
      itemName: "省直企业养老保险待遇查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B010201",
      isLogin: 1,
    },
    {
      itemName: "个人医保账户查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=202107280013",
      isLogin: 1,
    },
    {
      itemName: "人事考试成绩查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=B040102",
      isLogin: 0,
    },
    {
      itemName: "职业技能证书查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=107010",
      isLogin: 0,
    },
    {
      itemName: "企业信息查询",
      itemUrl: "/webview/bmfw/bmfw_check.html?bmfwId=20191127142524125",
      isLogin: 0,
    },
    {
      itemName: "新装用水申请",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429021snj/snj-xzyssq//index.html",
      isLogin: 1,
    },
    {
      itemName: "新装用气申请",
      itemUrl: "http://zwfw.hubei.gov.cn/dsbmfw/429021snj/snj-xzyqsq/index.html",
      isLogin: 1,
    },
    ],
  },
  ];

  var customersServiceHtml = "";
  customersServiceHtml += " <ul class='swiperbmfwUl'>";
  if (completeRegionCode.indexOf("429006") != -1) {
    completeRegionCode = completeRegionCode.substring(0, 6);
  } else if (completeRegionCode.indexOf("429004") != -1) {
    completeRegionCode = completeRegionCode.substring(0, 6);
  } else if (completeRegionCode.indexOf("429005") != -1) {
    completeRegionCode = completeRegionCode.substring(0, 6);
  } else if (completeRegionCode.indexOf("429021") != -1) {
    completeRegionCode = completeRegionCode.substring(0, 6);
  } else {
    completeRegionCode = completeRegionCode.substring(0, 4);
  }
  for (var j = 0; j < customersService.length; j++) {
    var element = customersService[j];
    if (completeRegionCode == element.regionCode) {
      for (var i = 0; i < element.serviceList.length; i++) {
        var dataitem = element.serviceList[i];
        // console.log(dataitem, "element");
        // customersServiceHtml += '<li>' + dataitem.itemName + '</li>'
        customersServiceHtml +=
          '<li class="bmlisttt" url="' +
          dataitem.itemUrl +
          '" data-isLogin="' +
          dataitem.isLogin +
          '" title="' +
          dataitem.itemName +
          '">' +
          dataitem.itemName +
          "</li>";
      }
    }
  }
  customersServiceHtml += "</ul>";
  //   console.log(customersServiceHtml);
  $(".swiper-bmfw .swiper-wrapper").html(customersServiceHtml);

  // 便民服务跳转
  // $(".bmlisttt").on("click", function () {
  //   debugger;
  //   var openUrl = $(this).attr("url");
  //   var isLogin = $(this).attr("data-isLogin");
  //   if (isLogin == "1") {
  //     if (checkLogin(true, openUrl, true)) {
  //       window.open(openUrl);
  //     }
  //   } else {
  //     window.open(openUrl);
  //   }
  // });

  // 个人服务法人服务部门服务的切换
  $(".newGrFr_top h3").on("click", function () {
    $(this).addClass("active").siblings().removeClass("active");
    $(".swiperbmfwUl").html();
  });

  // var ScrrenWidth =  $(window).resize().width
  // 关于轮播新的逻辑代码
  var screenWidth = $(window).width();
  // console.log(screenWidth,'screenWidth',tsqzDataList)
  // 首页响应式-1024（版心952） 多加18px
  if (screenWidth > 1024 && screenWidth <= 1365) {
    UlHtml(tsqzDataList.slice(0,6));
  } else if (screenWidth >= 768 && screenWidth <= 1023) {
    // 特色服务专区的轮播
    $(".swiper-tsqz .swiper-wrapper").html("");
    // var pageTotal = Math.ceil(count / grfr_total)   // 获取总页数
    var pageTotal = Math.ceil(6 / 2); // 获取总页数
    if ($(".swiper-tsqz .swiper-wrapper .swiper-slide").length <= 0) {
      for (var i = 0; i < pageTotal; i++) {
        var swiper_slide = document.createElement("div");
        $(swiper_slide).attr("class", "swiper-slide");
        $(".swiper-tsqz .swiper-wrapper").append(swiper_slide);
      }
    }
    for (var m = 0; m < pageTotal; m++) {
      var tsqzDataHtml = '<ul class="swiperTsqzUl">';
      for (var j = 0; j < tsqzDataList.length; j++) {
        var ListItem = tsqzDataList[j];
        if (Math.floor(j / 2) == m) {
          if (ListItem.serviceType == 1) {//普通外链
            tsqzDataHtml += "<li title='" + ListItem.title + "' path='" + ListItem.url + "'>";
            // tsqzDataHtml += '<a href="' + ListItem.url + '" target="_blank" rel="noopener noreferrer">';
            tsqzDataHtml += '<a href="javascript:void(0)"  onclick="gowl(\'' + ListItem.url + '\',' + ListItem.isLogin + ')">';
            tsqzDataHtml += "<p>";
            tsqzDataHtml += "<span>" + ListItem.title + "</span>";
            if (ListItem.hot == true) {
              tsqzDataHtml +=
                '<img src="/images/newIndex/index_tszq/hot_new.png" alt="">';
            }
            tsqzDataHtml += "</p>";
            tsqzDataHtml += "<p>";
            tsqzDataHtml += "" + ListItem.content + "";
            tsqzDataHtml += "</p>";
            tsqzDataHtml += '<p style="display:none;">';
            tsqzDataHtml +=
              '<img src="/images/newIndex/index_tszq/xh_new.png" alt="">';
            tsqzDataHtml += "<span>" + ListItem.serviceNum + "</span>";
            tsqzDataHtml += "</p>";
            tsqzDataHtml += "<p>";
            tsqzDataHtml += '<button>去看看</button>';
            tsqzDataHtml +=
              '<img style="width:20px;height:10px" src="/images/newIndex/index_tszq/qkk_new.png" alt="">';
            tsqzDataHtml += "</p>";
            tsqzDataHtml += '<img class="pic-bg" src="' + ListItem.imgurl + '" alt="">';
            if (ListItem.new == true) {
              tsqzDataHtml +=
                '<img class="shangxin" src="/images/newIndex/index_tszq/shangxin_new.png" alt="">';
            }
            tsqzDataHtml += "</a></li>";
          } else {
            tsqzDataHtml += "<li title='" + ListItem.title + "' path='" + ListItem.url + "'>";
            // tsqzDataHtml += '<a href="' + ListItem.url + '" target="_blank" rel="noopener noreferrer">';
            tsqzDataHtml += '<a href="javascript:void(0)"  onclick="getzqpath(\'' + ListItem.uniqueID + '\')">';
            tsqzDataHtml += "<p>";
            tsqzDataHtml += "<span>" + ListItem.title + "</span>";
            if (ListItem.hot == true) {
              tsqzDataHtml +=
                '<img src="/images/newIndex/index_tszq/hot_new.png" alt="">';
            }
            tsqzDataHtml += "</p>";
            tsqzDataHtml += "<p>";
            tsqzDataHtml += "" + ListItem.content + "";
            tsqzDataHtml += "</p>";
            tsqzDataHtml += '<p style="display:none;">';
            tsqzDataHtml +=
              '<img src="/images/newIndex/index_tszq/xh_new.png" alt="">';
            tsqzDataHtml += "<span>" + ListItem.serviceNum + "</span>";
            tsqzDataHtml += "</p>";
            tsqzDataHtml += "<p>";
            tsqzDataHtml += '<button>去看看</button>';
            tsqzDataHtml +=
              '<img style="width:20px;height:10px" src="/images/newIndex/index_tszq/qkk_new.png" alt="">';
            tsqzDataHtml += "</p>";
            tsqzDataHtml += '<img class="pic-bg" src="' + ListItem.imgurl + '" alt="">';
            if (ListItem.new == true) {
              tsqzDataHtml +=
                '<img class="shangxin" src="/images/newIndex/index_tszq/shangxin_new.png" alt="">';
            }
            tsqzDataHtml += "</a></li>";
          }
        }
      }
      tsqzDataHtml += "</ul>";

      $(".swiper-tsqz .swiper-wrapper")
        .find(".swiper-slide")
        .eq(m)
        .html(tsqzDataHtml);
    }
    var mySwiper = new Swiper(".swiper-tsqz", {
      loop: true, // 循环模式选项
      navigation: {
        nextEl: "#tc_next",
        prevEl: "#tc_prev",
        // disabledClass: 'my-button-disabled',
      },
      // 如果需要分页器
      pagination: {
        el: "#tc_pagination",
        pagination: "#tc_pagination",
        paginationClickable: "#tc_pagination",
        clickable: true,
      },
    });

    // var bmfwHtml = '<ul class="swiperbmfwUl swiper-slide">'
    // for (var i = 0; i < customersService.length; i++) {
    //     var item = customersService[i];
    //     if (i < 6) {
    //         bmfwHtml += '<li>' + item.itemName + '</li>'
    //     }
    // }
    // bmfwHtml += '</ul>'

    // bmfwHtml += '<ul class="swiperbmfwUl swiper-slide">'
    // for (var i = 0; i < customersService.length; i++) {
    //     var item = customersService[i];
    //     if (i >= 6) {
    //         bmfwHtml += '<li>' + item.itemName + '</li>'
    //     }
    // }
    // bmfwHtml += '</ul>'
    // $('.swiper-bmfw .swiper-wrapper').html(bmfwHtml);
    // var mySwiper = new Swiper('.swiper-bmfw', {
    //     loop: true, // 循环模式选项
    //     navigation: {
    //         nextEl: '#bm_next',
    //         prevEl: '#bm_prev',
    //         // disabledClass: 'my-button-disabled',
    //     },
    //     // 如果需要分页器
    //     pagination: {
    //         el: '#bm_pagination',
    //         pagination: '#bm_pagination',
    //         paginationClickable: '#bm_pagination',
    //         clickable: true,
    //     },

    // })
  } else if (screenWidth < 768) {
    // $('.gr_cyfw').show();

    // 特色服务专区的轮播
    $(".swiper-tsqz .swiper-wrapper").html("");
    // var pageTotal = Math.ceil(count / grfr_total)   // 获取总页数
    var pageTotal = Math.ceil(6 / 1); // 获取总页数
    // if ($('.swiper-tsqz .swiper-wrapper .swiper-slide').length <= 0) {
    for (var i = 0; i < pageTotal; i++) {
      var swiper_slide = document.createElement("div");
      $(swiper_slide).attr("class", "swiper-slide");
      $(".swiper-tsqz .swiper-wrapper").append(swiper_slide);
    }
    // }
    for (var m = 0; m < pageTotal; m++) {
      var tsqzDataHtml = '<ul class="swiperTsqzUl">';

      for (var j = 0; j < tsqzDataList.length; j++) {
        var ListItem = tsqzDataList[j];
        if (Math.floor(j / 1) == m) {
          if (ListItem.serviceType == 1) {//普通外链
            tsqzDataHtml += "<li title='" + ListItem.title + "' path='" + ListItem.url + "'>";
            // tsqzDataHtml += '<a href="' + ListItem.url + '" target="_blank" rel="noopener noreferrer">';
            tsqzDataHtml += '<a href="javascript:void(0)"  onclick="gowl(\'' + ListItem.url + '\',' + ListItem.isLogin + ')">';
            tsqzDataHtml += "<p>";
            tsqzDataHtml += "<span>" + ListItem.title + "</span>";
            if (ListItem.hot == true) {
              tsqzDataHtml +=
                '<img src="/images/newIndex/index_tszq/hot_new.png" alt="">';
            }
            tsqzDataHtml += "</p>";
            tsqzDataHtml += "<p>";
            tsqzDataHtml += "" + ListItem.content + "";
            tsqzDataHtml += "</p>";
            tsqzDataHtml += '<p style="display:none;">';
            tsqzDataHtml +=
              '<img src="/images/newIndex/index_tszq/xh_new.png" alt="">';
            tsqzDataHtml += "<span>" + ListItem.serviceNum + "</span>";
            tsqzDataHtml += "</p>";
            tsqzDataHtml += "<p>";
            tsqzDataHtml += '<button>去看看</button>';
            tsqzDataHtml +=
              '<img style="width:20px;height:10px" src="/images/newIndex/index_tszq/qkk_new.png" alt="">';
            tsqzDataHtml += "</p>";
            tsqzDataHtml += '<img class="pic-bg" src="' + ListItem.imgurl + '" alt="">';
            if (ListItem.new == true) {
              tsqzDataHtml +=
                '<img class="shangxin" src="/images/newIndex/index_tszq/shangxin_new.png" alt="">';
            }
            tsqzDataHtml += "</a></li>";
          } else {
            tsqzDataHtml += "<li title='" + ListItem.title + "' path='" + ListItem.url + "'>";
            // tsqzDataHtml += '<a href="' + ListItem.url + '" target="_blank" rel="noopener noreferrer">';
            tsqzDataHtml += '<a href="javascript:void(0)"  onclick="getzqpath(\'' + ListItem.uniqueID + '\')">';
            tsqzDataHtml += "<p>";
            tsqzDataHtml += "<span>" + ListItem.title + "</span>";
            if (ListItem.hot == true) {
              tsqzDataHtml +=
                '<img src="/images/newIndex/index_tszq/hot_new.png" alt="">';
            }
            tsqzDataHtml += "</p>";
            tsqzDataHtml += "<p>";
            tsqzDataHtml += "" + ListItem.content + "";
            tsqzDataHtml += "</p>";
            tsqzDataHtml += '<p style="display:none;">';
            tsqzDataHtml +=
              '<img src="/images/newIndex/index_tszq/xh_new.png" alt="">';
            tsqzDataHtml += "<span>" + ListItem.serviceNum + "</span>";
            tsqzDataHtml += "</p>";
            tsqzDataHtml += "<p>";
            tsqzDataHtml += '<button>去看看</button>';
            tsqzDataHtml +=
              '<img style="width:20px;height:10px" src="/images/newIndex/index_tszq/qkk_new.png" alt="">';
            tsqzDataHtml += "</p>";
            tsqzDataHtml += '<img class="pic-bg" src="' + ListItem.imgurl + '" alt="">';
            if (ListItem.new == true) {
              tsqzDataHtml +=
                '<img class="shangxin" src="/images/newIndex/index_tszq/shangxin_new.png" alt="">';
            }
            tsqzDataHtml += "</a></li>";
          }
        }
      }
      tsqzDataHtml += "</ul>";

      $(".swiper-tsqz .swiper-wrapper")
        .find(".swiper-slide")
        .eq(m)
        .html(tsqzDataHtml);
    }
    var mySwiper = new Swiper(".swiper-tsqz", {
      loop: true, // 循环模式选项
      navigation: {
        nextEl: "#tc_next",
        prevEl: "#tc_prev",
        // disabledClass: 'my-button-disabled',
      },
      // 如果需要分页器
      pagination: {
        el: "#tc_pagination",
        pagination: "#tc_pagination",
        paginationClickable: "#tc_pagination",
        clickable: true,
      },
    });

    // var bmfwHtml = '<ul class="swiperbmfwUl swiper-slide">'
    // for (var i = 0; i < customersService.length; i++) {
    //     var item = customersService[i];
    //     if (i < 4) {
    //         bmfwHtml += '<li>' + item.itemName + '</li>'
    //     }
    // }
    // bmfwHtml += '</ul>'

    // bmfwHtml += '<ul class="swiperbmfwUl swiper-slide">'
    // for (var i = 0; i < customersService.length; i++) {
    //     var item = customersService[i];
    //     if (i >= 4) {
    //         bmfwHtml += '<li>' + item.itemName + '</li>'
    //     }
    // }
    // bmfwHtml += '</ul>'
    // $('.swiper-bmfw .swiper-wrapper').html(bmfwHtml);
    // var mySwiper = new Swiper('.swiper-bmfw', {
    //     loop: true, // 循环模式选项
    //     navigation: {
    //         nextEl: '#bm_next',
    //         prevEl: '#bm_prev',
    //         // disabledClass: 'my-button-disabled',
    //     },
    //     // 如果需要分页器
    //     pagination: {
    //         el: '#bm_pagination',
    //         pagination: '#bm_pagination',
    //         paginationClickable: '#bm_pagination',
    //         clickable: true,
    //     },

    // })
  
  } else {//大于1366尺寸，显示数量
    // console.log(tsqzDataList.slice(0,6))
    UlHtml(tsqzDataList.slice(0,6));
  }

  function UlHtml(tsqzDataList) {
    $(".swiper-tsqz .swiper-wrapper").html("");
    var tsqzDataHtml = "";
    tsqzDataHtml += '<ul class="swiperTsqzUl">';
    for (var i = 0; i < tsqzDataList.length; i++) {
      var ListItem = tsqzDataList[i];
      if (ListItem.serviceType == 1) {//普通外链
        tsqzDataHtml += "<li title='" + ListItem.title + "' path='" + ListItem.url + "'>";
        // tsqzDataHtml += '<a href="' + ListItem.url + '" target="_blank" rel="noopener noreferrer">';
        tsqzDataHtml += '<a href="javascript:void(0)"  onclick="gowl(\'' + ListItem.url + '\',' + ListItem.isLogin + ')">';
        tsqzDataHtml += "<p>";
        tsqzDataHtml += "<span>" + ListItem.title + "</span>";
        if (ListItem.hot == true) {
          tsqzDataHtml +=
            '<img src="/images/newIndex/index_tszq/hot_new.png" alt="">';
        }
        tsqzDataHtml += "</p>";
        tsqzDataHtml += "<p>";
        tsqzDataHtml += "" + ListItem.content + "";
        tsqzDataHtml += "</p>";
        tsqzDataHtml += '<p style="display:none;">';
        tsqzDataHtml +=
          '<img src="/images/newIndex/index_tszq/xh_new.png" alt="">';
        tsqzDataHtml += "<span>" + ListItem.serviceNum + "</span>";
        tsqzDataHtml += "</p>";
        tsqzDataHtml += "<p>";
        tsqzDataHtml += '<button>去看看</button>';
        tsqzDataHtml +=
          '<img style="width:20px;height:10px" src="/images/newIndex/index_tszq/qkk_new.png" alt="">';
        tsqzDataHtml += "</p>";
        tsqzDataHtml += '<img class="pic-bg" src="' + ListItem.imgurl + '" alt="">';
        if (ListItem.new == true) {
          tsqzDataHtml +=
            '<img class="shangxin" src="/images/newIndex/index_tszq/shangxin_new.png" alt="">';
        }
        tsqzDataHtml += "</a></li>";
      } else {
        tsqzDataHtml += "<li title='" + ListItem.title + "' path='" + ListItem.url + "'>";
        // tsqzDataHtml += '<a href="' + ListItem.url + '" target="_blank" rel="noopener noreferrer">';
        tsqzDataHtml += '<a href="javascript:void(0)"  onclick="getzqpath(\'' + ListItem.uniqueID + '\')">';
        tsqzDataHtml += "<p>";
        tsqzDataHtml += "<span>" + ListItem.title + "</span>";
        if (ListItem.hot == true) {
          tsqzDataHtml +=
            '<img src="/images/newIndex/index_tszq/hot_new.png" alt="">';
        }
        tsqzDataHtml += "</p>";
        tsqzDataHtml += "<p>";
        tsqzDataHtml += "" + ListItem.content + "";
        tsqzDataHtml += "</p>";
        tsqzDataHtml += '<p style="display:none;">';
        tsqzDataHtml +=
          '<img src="/images/newIndex/index_tszq/xh_new.png" alt="">';
        tsqzDataHtml += "<span>" + ListItem.serviceNum + "</span>";
        tsqzDataHtml += "</p>";
        tsqzDataHtml += "<p>";
        tsqzDataHtml += '<button>去看看</button>';
        tsqzDataHtml +=
          '<img style="width:20px;height:10px" src="/images/newIndex/index_tszq/qkk_new.png" alt="">';
        tsqzDataHtml += "</p>";
        tsqzDataHtml += '<img class="pic-bg" src="' + ListItem.imgurl + '" alt="">';
        if (ListItem.new == true) {
          tsqzDataHtml +=
            '<img class="shangxin" src="/images/newIndex/index_tszq/shangxin_new.png" alt="">';
        }
        tsqzDataHtml += "</a></li>";
      }
    }
    tsqzDataHtml += "</ul>";
    $(".swiper-tsqz .swiper-wrapper").prepend(tsqzDataHtml);
  }

  window.screenWidth = $(window).width();
  var regionCode_q = completeRegionCode.substr(0, 6);
  var slidesPerView_zq = 1
  var yslb_zt_Loop = false
  var ysb_zt_autoplay = 0
  if (screenWidth > 1024) {
    slidesPerView_zq = 2;
    slidesPerView_ztlb = 4;
    allowTouchMove = false;
    yslb_zt_Loop = false;
    ysb_zt_autoplay = 0;

    // debugger;
    // if (regionCode_q == "420000") {
    //   $(".heyun").show();
    // } else {
    //   $(".heyun").hide();
    // }


    // $('.zhounian_100').children('img').attr('style', 'width: 165px;position: absolute;top:22px;right:  15%;')
  } else if (screenWidth < 1023 && screenWidth >= 768) {
    // slidesPerView_zq = 1;
    // slidesPerView_ztlb = 4;
    // allowTouchMove = false;
    // yslb_zt_Loop = false;
    // ysb_zt_autoplay = 3000;

    // $(".heyun").hide();
    $(".heyun").css({
      'left': '167px'
    });
    // 悬浮图标
    // $('.zhounian_100').children('img').attr('style', 'width: 165px;position: absolute;top:82%;right: 20%;')
  } else if (screenWidth < 768) {
    $(".heyun").hide();
  } else {
    slidesPerView_zq = 1;
    slidesPerView_ztlb = 1;
    allowTouchMove = true;
    yslb_zt_Loop = true;
    ysb_zt_autoplay = 3000;

    // $(".heyun").hide();
    // $('.zhounian_100').children('img').attr('style', 'width:30%;position: absolute;top:40%;right:10%;')
  }

  if (completeRegionCode == "420700000000") {
    mySwiper_zq = new Swiper("#swiper_zq", {
      loop: true, // 循环模式选项
      // autoplay: {
      // autoplay:false,
      // disableOnInteraction: false,
      // delay: 4000,
      // },
      autoplay: false,
      pagination: {
        el: "#pagination_zq",
        clickable: true,
      },
      slidesPerView: slidesPerView_zq, //'auto'
      paginationClickable: true,
      spaceBetween: 24,
      // 如果需要分页器
      observer: true,
      observerParents: true,
    });
  } else {
    mySwiper_zq = new Swiper("#swiper_zq", {
      loop: true, // 循环模式选项
      autoplay: {
        disableOnInteraction: false,
        delay: 4000,
      },
      pagination: {
        el: "#pagination_zq",
        clickable: true,
      },
      slidesPerView: slidesPerView_zq, //'auto'
      paginationClickable: true,
      spaceBetween: 24,
      // 如果需要分页器
      observer: true,
      observerParents: true,
    });
  }

  mySwiper_yslb = new Swiper("#swiper_yslb", {
    loop: yslb_zt_Loop, // 循环模式选项
    autoplay: {
      disableOnInteraction: false,
      delay: ysb_zt_autoplay,
    },
    pagination: {
      el: "#pagination_yslb",
      clickable: true,
    },
    slidesPerView: slidesPerView_ztlb, //'auto'
    //slidesPerView : 3.7,
    //如果设置为auto（例如制作全屏展示时的页脚部分），最后一个slide在键盘或鼠标滚动时可能会直接跳到倒数第三个slide，
    //此时可以手动设置activeIndex解决，如下
    // onTransitionEnd: function (swiper) {
    //     if (swiper.progress == 1) {
    //         swiper.activeIndex = swiper.slides.length - 1
    //     }
    // },
    allowTouchMove: allowTouchMove,
    paginationClickable: true,
    spaceBetween: 24,
    // 如果需要分页器
    observer: true,
    observerParents: true,
  });

  // //将滑动的图片进行改变
  // $('.chgd_a').hover(function () {
  //     $(this).children('.chgd_').css('color', '#FF5B24')
  //     $(this).children('img').attr('src', '/images/ico-huadongJT.png')

  //     if ($(this).hasClass('yslb_a') || $(this).hasClass('yslb_')) {
  //         $(this).css('border', '1px solid #FF5B24')
  //     }
  // })
  // $('.chgd_a').mouseleave(function () {
  //     $(this).children('.chgd_').css('color', '#000000');
  //     $(this).children('img').attr('src', '/images/ico-jiantou_index.png');
  //     if ($(this).hasClass('yslb_a') || $(this).hasClass('yslb_')) {
  //         $(this).css('border', ' 1px solid rgba(0, 0, 0, 0.15)')
  //     }
  // })

  // 神策数据的采集
  $(".rcfw").click(function () {
    var userid = window.uias_userid ? window.uias_userid : "";
    // console.log(userid, 'userid')
    if (sensors != undefined) {
      sensors.quick("autoTrackSinglePage", {
        uiasId: userid,
        transactCode: "",
        bsNum: "",
      });
    }
  });
});

// 咨询投诉建议
function txtsjy(type) {
  if (checkLogin(true, "/webview/bszn/zxts.html?consultType=" + type)) {
    location.href = "/webview/bszn/zxts.html?consultType=" + type;
  }
}

//红色专区
// function hszq() {
//     location.href = "/webview/hszq/hszq.html"
// }
$(".swiperBox").mouseover(function (e) {
  $("#tszqSwiper-next").show();
  $("#tszqSwiper-prev").show();
});
$(".swiperBox").mouseout(function (e) {
  $("#tszqSwiper-next").hide();
  $("#tszqSwiper-prev").hide();
});

// 特色专区跳转
function gowl(url, isLogin) {
  console.log(url, isLogin)
  if (isLogin) {
    checkLoginTo(url)
  } else {
    window.open(url);
  }
}

function checkLoginTo(url) {
  if (checkLogin(true, url, true)) {
    // window.open('/webview/tzxm/tzxm.html');
    window.open(url);
  }
}
// 查询专区链接
function getzqpath(uniqueID, isLogin) {
  $.ajax({
    url: '/web/external/openPlatform/formPath.jspc',
    data: {
      type: 2,
      uniqueID: uniqueID
    },
    type: 'get',
    crossDomain: true,
    //async:false,
    dataType: 'json',
    success: function (data) {
      console.log(data, '获取专区地址');
      if (data.code == "1") {
        // if(isLogin){
        //     checkLoginTo(data.data)
        // }
        // $("#tzgc").attr("src", data.data);
        window.open(data.data)
      } else {
        // console.log("自定义表单提供参数加载失败："+data.msg);
      }
      // wssb_zdy_userparam_flag=true;
    },
    error: function (e) {
      // wssb_zdy_userparam_flag="error";
      // console.log("自定义表单提供参数加载失败！");
      console.log(e);
    }
  });
}




var sxUserType = '1'
var sxQhCode = ''
  var sxQhCj = ''
// 选择区划新增对应的事项展示  2024/9/4
$('.userTypebox').click(function () {
  // 移除所有 .userTypebox 元素的 active 类
  $('.userTypebox').removeClass('chooseUserType');
  sxUserType = $(this).data('value');
  // 为被点击的元素添加 active 类
  $(this).addClass('chooseUserType');
  console.log(sxUserType, 'sxUserType')
  getItemList()
});


// 选择小标题事项展示  2024/9/4
$('.sonList').click(function () {
  stopPropagationByBrowser();
  // 移除所有 .userTypebox 元素的 active 类
  $('.sonList').removeClass('org_title');
  // 为被点击的元素添加 active 类
  $(this).addClass('org_title');
});



function getItemList() {
  console.log(sxQhCode,'codeee')
  var pageForItemSearch = {
    "grade": '',//行使层级
    "orgCode": '', //部门编码
    "isOnline": '',//是否网办
    "serviceGr": sxUserType==1?'1':'',//是否是个人
    "serviceFr": sxUserType==2?'1':'',//是否是法人
    "subjectIdsGr": '',//个人主题id
    "subjectIdsFr": '',//法人主题id
    "taskType": '',//事项类型
    "regionCode": sxQhCode,//区划     区划查找有问题
    "areaGrade": sxQhCj,//区划等级
    "currentPage": 1,//当前页
    "pageSize":12,//页面大小
    "onlyLocalLevel": "1",//仅查本级
    "onlyGrfRSearch": "1"//是否是个人/法人查询（0否，1是）
  };
  $.ajax({
    url: "/web/bszn/item_project",
    type: "POST",
    dataType: "json",
    timeout: 2000,
    data: pageForItemSearch,
    success: function (data) {
      //layer_close(index);
      console.log(data);
      if (data.code == "1") {
        var YWarr = data.data.records;
        var html = "";
        var ahtml = "";
        let objNameCode = {
          "420222040400": "𣲗山村委会",
          "420222040000": "𣲗源口镇",
          "420222042100": "𣲗源口村委会"
        }
        if (YWarr != null && YWarr.length != 0) {
          var temp = '';
          for (var i = 0; i < YWarr.length; i++) {
            var SXname = YWarr[i].TASKNAME;//事项名称
            var SXcode = YWarr[i].TASKCODE//事项编码
            if (SXname == "" || SXname == undefined) {
              SXname = "事项名为空"
            }
            if (temp != SXcode) {
              let REGION_NAME = YWarr[i].REGION_NAME
              if (objNameCode[YWarr[i].REGION_CODE]) {
                REGION_NAME = objNameCode[YWarr[i].REGION_CODE]
              }
              html += '<div class="sxList" onclick="showDetail(this)" taskCode=' + SXcode + '>'+ SXname + '</div>';
              temp = SXcode;
            }

          }
          $('.sxListBox').html(html)
        } else {
          
        }
      } else {
        
      }
    },
    error: function (e) {
      console.log("事项检索出错了!");
    }
  })
}
var sx_taskCode = ''
function showDetail(e){
  console.log('打开zz',$(e).attr("taskCode"),$(e).text())
  sx_taskCode = $(e).attr("taskCode")
  $('.sx_title').text($(e).text())
  $('.zz_box').show()
  show_itemPage_es(sx_taskCode)
}

$('.sxClose').click(function(){
  stopPropagationByBrowser();
  $('.zz_box').hide()

})
$('.sxMoreBox').click(function(){
  stopPropagationByBrowser();
  $('.zz_box').hide()
  // $('#fww_url').click()
  var regionCode = $("#fww_url").attr("data-code");
        var regionName = $("#fww_url").attr("data-name");
        var regionGrade = $("#fww_url").attr("data-grade");
        setSessionRegionCode(regionCode,regionName,regionGrade);
  if(sxUserType==1){
    window.open('/webview/fw/grfw.html');
  }else{
    window.open('/webview/fw/frfw.html');
  }
  
})
$('.sxDetailBox').click(function(){
  stopPropagationByBrowser();
})

//通过数据库查询办理项分页数据
function show_itemPage_es(taskCode) {
  var pageForItemSearch = {
      "taskcode": taskCode,
      "currentPage": '1',//当前页
      "pageSize": '99',//页面大小
  };
  $.ajax({
      url: "/web/bszn/item_project_transaction",
      type: "POST",
      dataType: "json",
      timeout: 3000,
      //contentType:'application/json;charset=utf-8',
      data: pageForItemSearch,
      success: function (data) {
          console.log(data);
          if (data.code == "1") {
              var tdata = data.data.records;
              var html = "";
              if (tdata) {
                  for (var i = 0; i < tdata.length; i++) {
                      html += '<div class="sxxxList" onclick="goDetail(\'' + tdata[i].TRANSACTCODE + '\')">'+ tdata[i].TRANSACTNAME + '</div>';
                    
                  };
                  $('.sxxxListbox').html(html)


              } else {
                  console.log(data.data.error);
                  layer_msg("暂无业务办理项");
              }
          } else {
              layer_msg("获取办理项失败：" + data.msg);
          }
      },
      error: function (e) {
          console.log(e);
          layer_msg('获取办理项异常！');
      }
  })
}

function goDetail(e){
  $('.zz_box').hide()
  window.open('/webview/bszn/bsznpage.html?transactCode=' + e);
}