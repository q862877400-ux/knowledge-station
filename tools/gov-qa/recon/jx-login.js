// 登陆
var token = window.localStorage.getItem("token");
if (!token || (token && token == 'null')) {
  //优先本地已有的localStorage，防止网址直接输入token导致页面显示登陆失败
  token = commonApi.getParams('token');
  // 把token值存入localStorage
  window.localStorage.setItem("token", token);
}
token = window.localStorage.getItem("token");
// console.log(token)

if (token && token !== 'null') {
  //有token值就会调用登陆接口判断是否登陆
  userloginCallback()
  getUserInfo(succCallback, failCallback);
} else {
  useroutCallback()
  failCallback();
}


//获取用户信息
function getUserInfo(succCallback, failCallback) {
  $.ajax({
    type: "GET",
    url: "/u/ssoLogin/loadUserInfo",
    // async: true,
    timeout: 60 * 1000 * 3,
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      "code": window.localStorage.getItem("token")
    },
    success: function (res) {
      // console.log('res', res);
      if (res.code == 1) {
        var data = res.data,
          userVO = data && data.userVO; //用户数据
        // console.log(userVO)
        succCallback && succCallback(userVO);
      } else {
        failCallback && failCallback(res)
      }
    },
    error: function error(err) {
      // console.log('err',err);
      failCallback && failCallback(err)
    }
  });
}

//登陆成功回调
function succCallback(userInfo) {
  // console.log('登陆成功')
  window.localStorage.setItem("token", window.localStorage.getItem("token"));
  // console.log(userInfo)
  $('.header-toolbar-r li.user').addClass('logined split').html('您好，<a class="username" target="_blank" href="/UserCenter/">' + commonApi.filtersName(userInfo.name) + '</a><a href="javascript:void(0);" class="loginout-btn">退出登录</div>');

  $('.loginout-btn').click(function () {
    $.ajax({
      url: "/u/ssoLogin/logout",
      type: "get",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "code": window.localStorage.getItem("token")
      },
      success: function (res) {
        // console.log(res)
        window.localStorage.removeItem("token"); //删除token，删除之后值是'null'字符串
        location.reload();
      },
      error: function error(err) {}
    });
  })
}

//登陆失败回调
function failCallback(res) {
  // console.log('登陆失败')
  window.localStorage.removeItem("token"); //删除token，删除之后值是'null'字符串
  var _href = window.location.href,
    pathname = window.location.pathname
    var loginUrl = "/u/ssoLogin/loginBtn?dataId=" + uuid() + "&r_url=" + _href;
  $('.header-toolbar-r li.user').html('<a target="_blank" href="'+ loginUrl +'" title="用户空间"><span>用户空间</span></a>');

  if (pathname == '/jxsrmzf/mail/form.html'||pathname == '/jxsrmzf/wssq/pc/list.html') {
    window.location.href = loginUrl;
  }
}

function uuid() {
  var s = [];
  var hexDigits = "0123456789abcdef";
  for (var i = 0; i < 32; i++) {
    s[i] = hexDigits.substr(Math.floor(Math.random() * 0x10), 1);
  }
  s[14] = "4"; // bits 12-15 of the time_hi_and_version field to 0010
  s[19] = hexDigits.substr((s[19] & 0x3) | 0x8, 1); // bits 6-7 of the clock_seq_hi_and_reserved to 01
  s[8] = s[13] = s[18] = s[23];
  var uuid = s.join("");
  return uuid;
}

// 用户中心回调登录
function userloginCallback(){
    $.ajax({
      url:'/usapi/ssoLogin/login?dataId=' + uuid()+'&token='+ token +'',
      type: "get",
      contentType:'application/json',
      dataType:'json',
      success: function (res) {
        //console.log(res)
        
      }, 
      error: function error(err) {
        console.log('err: ', err);
      }
    });
}

// 用户中心回调退出
function useroutCallback(){
  $.ajax({
    url:'/usapi/ssoLogin/logout',
    type: "get",
    contentType:'application/json',
    dataType:'json',
    success: function (res) {
      //console.log(res)
      
    }, 
    error: function error(err) {
      console.log('err: ', err);
    }
  });
}