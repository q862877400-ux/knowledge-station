var ajaxFun = {
  ip: [ '' ],

  // 获取数据
  getData: function(url, data, cb, failCb){
    var _this = this;
    $.ajax({
      type: "post",
      url: _this.ip[0] + url,
      data: data,
      dataType: "json",
      contentType: 'application/json',
      success: function (res) {
        if( res.status && res.status == 'success' ){
          cb(res.data);
        }else{
          if(failCb){
            failCb(res)
          }else{
            cb(res)
          }
          
        }
      },
      error: function (data) {
        console.log( data )
      }
    });
  },
  getData_get: function getData_get(url, cb, contentType, isThisIp) {
    var _this = this;
    // var ip = isThisIp ? _this.ip : _this.url;
    var ip = '';
    $.ajax({
      type: "get",
      url: ip + url,
      dataType: "json",
      contentType: contentType,
      success: function success(res) {
        if (res.status == 'success') {
          cb(res.data);
        } else {
          cb(res);
        }
      },
      error: function error(data) {
        console.log(data);
      }
    });
  },

  // 获取地址栏参数
  getUrlParam: function(name) {
    var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)"); //构造一个含有目标参数的正则表达式对象
    var r = window.location.search.substr(1).match(reg); //匹配目标参数
    if (r != null)
    {return decodeURIComponent(r[2]); }
    return null; //返回参数值
  },


  clearP: function(p){
    return p.replace(/<p>/g, '').replace(/<\/p>/g, '');
  },

  isMobile: function () {
    return (/iPad|iPhone|Android|Windows Phone|Nokia/).test(navigator.userAgent);
  },

  phoneFun: function(phones){
    var myreg = /^[1][3,4,5,7,8,9][0-9]{9}$/;
    return myreg.test(phones);
  },

  testIdNo: function(idNo){
    var regIdNo = /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/; 
    return regIdNo.test(idNo);
  },
  
  // 防抖函数
  debounce(fn, wait, immediate) {
    var timeout, result;
    var debounced = function () {
      //改变执行函数内部this的指向，让this指向container
      var context = this;
      //参数
      var args = arguments;
      if (timeout) clearTimeout(timeout);
      if (immediate) {
        var callNow = !timeout;
        timeout = setTimeout(() => {
          timeout = null;
        }, wait);
        if (callNow) {
          result = fn.apply(context, args)
        }
      } else {
        timeout = setTimeout(() => {
          fn.apply(context, args)
        }, wait)
      }
      return result;
    }
    //取消防抖
    debounced.cancel = function () {
      clearTimeout(timeout)
      timeout = null;
    }
    return debounced;
  }
}

