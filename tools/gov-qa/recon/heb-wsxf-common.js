var uuid = ''; // 存储token值
var ztArr = ['提交成功', '办理中', '已办结', '超期未办结', '已催办']; // 案件状态
// ajax方法二次封装
function httpRequest(params) {
    var selector = $("body");
    if (params.needLoading) {
        if (params.hasOwnProperty("target")) {
            selector = params.target;
        }
        selector.addClass("load-indicator loading");
    }
    $.ajax({
        url: "/wsxf" + params.url,
        async: params.hasOwnProperty("async") ? params.async : true,
        contentType: params.hasOwnProperty("contentType") ? params.contentType :
            "application/x-www-form-urlencoded",
        dataType: 'json',
        headers: {
            "user-token": $.zui.store.get('user-token') ? $.zui.store.get('user-token') : ''
        },
        data: params.hasOwnProperty("data") ? params.data : {},
        timeout: params.timeout || 100000,
        method: params.method || 'POST',
        success: function (result, status) {
            if (params.hasOwnProperty("success")) {
                params.success(result, status);
            } else {
                new $.zui.Messager(result.msg, {
                    time: 2000,
                    close: false,
                    type: result.code == '200' ? 'success' : 'warning' // 定义消息图标
                });
            }
        },
        error: function (xhr, status, error) {
            console.log(xhr, status, error);
            if (params.hasOwnProperty("error")) {
                params.error(xhr, status, error);
            } else {
                new $.zui.Messager("数据异常，请联系管理员处理！", {
                    time: 2000,
                    close: false,
                    type: 'warning'
                });
            }
        },
        complete: function (xhr, status) {
            if (params.needLoading) {
                selector.removeClass("load-indicator loading");
            }
            if (params.hasOwnProperty("complete")) {
                params.complete(xhr, status);
            }
        }
    });
}

// 校验规则
function validateRules(value, flag) {
    if ([undefined, null, ''].indexOf(value) > -1) {
        return false;
    }
    var rules = "";
    switch (flag) {
        case 0: // 数字
            rules = /^[1-9][0-9]*$/;
            break;
        case 1: // 电话号码
            rules = /^((d{3,4}-)|d{3.4}-)?d{7,8}$/;
            break;
        case 2: // 手机号码
            rules = /^1(3|4|5|6|7|8|9)\d{9}$/;
            break;
        case 3: // 匹配正整数或正小数
            rules = /(^0\.[0-9]*$)|(^[1-9][0-9]*\.[0-9]*$)/;
            break;
        case 4: // 邮箱
            rules = /^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/;
            break;
        case 5: // 身份证号
            rules = /^[1-9]\d{5}(18|19|([23]\d))\d{2}((0[1-9])|(10|11|12))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/;
            break;
        case 6: // URL
            rules = /^[1-9]\d{5}(18|19|([23]\d))\d{2}((0[1-9])|(10|11|12))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/;
            break;
        case 7: // 邮政编码
            rules = /^[1-9][0-9]{5}$/;
            break;
        case 8: // 中文
            rules = /^[\u4e00-\u9fa5·•]{0,}$/;
            break;
    }
    if (!rules.test(value)) {
        return false;
    }
    if (flag == 5) {
        return idCardValid(value);
    }
    return true;
};

function idCardValid(id) {

    /* 15位身份证号转18位身份证号 */
    if (id && id.length == '15') {
        var arrInt = new Array(7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2);
        var arrCh = new Array('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2');
        var cardTemp = 0, i;
        var a18 = ""
        a18 = id.substr(0, 6) + '19' + id.substr(6, id.length - 6);
        for (i = 0; i < 17; i++) {
            cardTemp += a18.substr(i, 1) * arrInt[i];
        }
        a18 += arrCh[cardTemp % 11];
        id = a18
    }

    // 1 "验证通过!", 0 //校验不通过
    var format = /^(([1][1-5])|([2][1-3])|([3][1-7])|([4][1-6])|([5][0-4])|([6][1-5])|([7][1])|([8][1-2]))\d{4}(([1][9]\d{2})|([2]\d{3}))(([0][1-9])|([1][0-2]))(([0][1-9])|([1-2][0-9])|([3][0-1]))\d{3}[0-9xX]$/;
    // 号码规则校验
    if (!format.test(id)) {
        // return { 'status': 0, 'msg': '身份证号码不合规' };
        return false;
    }
    // 区位码校验
    // 出生年月日校验 前正则限制起始年份为1900;
    var year = id.substr(6, 4),// 身份证年
        month = id.substr(10, 2),// 身份证月
        date = id.substr(12, 2),// 身份证日
        time = Date.parse(month + '-' + date + '-' + year),// 身份证日期时间戳date
        now_time = Date.parse(new Date()),// 当前时间戳
        dates = (new Date(year, month, 0)).getDate();// 身份证当月天数
    if (time > now_time || date > dates) {
        // return { 'status': 0, 'msg': '出生日期不合规' }
        return false;
    }
    // 校验码判断
    var c = new Array(7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2);   // 系数
    var b = new Array('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2');  // 校验码对照表
    var id_array = id.split("");
    var sum = 0;
    for (var k = 0; k < 17; k++) {
        sum += parseInt(id_array[k]) * parseInt(c[k]);
    }
    if (id_array[17].toUpperCase() != b[sum % 11].toUpperCase()) {
        // return { 'status': 0, 'msg': '身份证校验码不合规' }
        return false;
    }
    // return { 'status': 1, 'msg': '校验通过' }
    return true;
}

// 生成顶部时钟
function watchWalk() {
    var nowDate = new Date();
    var y = nowDate.getFullYear();
    var m = nowDate.getMonth() < 9 ? '0' + (nowDate.getMonth() + 1) : nowDate.getMonth() + 1;
    var d = nowDate.getDate() < 10 ? '0' + nowDate.getDate() : nowDate.getDate();
    var w = nowDate.getDay();
    var arr = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    $(".clock-panel").text(y + '年' + m + '月' + d + '日 ' + arr[w]);
    setTimeout("watchWalk", 86400000);
}

// 生成uuid
function guid() {
    return 'xxxxxxxxxxxx4xxxyxxxxxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = Math.random() * 16 | 0,
            v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// 获取验证图片src
function getYzSrc() {
    uuid = guid();
    var url = '/wsxf/web/userapi/verifyImage?token=' + uuid;
    return url;
}

// 验证表单
function validateForm(xDOM) {
    var formdata = {}
    for (var i = 0; i < xDOM.length; i++) {
        var isVisible = xDOM.eq(i).is(":visible");
        var name = xDOM.eq(i).attr('name');
        var selectedname = xDOM.eq(i).attr('selectedname');
        if (isVisible) {
            var tagName = xDOM.eq(i)[0].tagName;
            // 判空校验
            if (((tagName == 'INPUT' || tagName == 'TEXTAREA') && xDOM.eq(i).val() == ""
                || tagName == 'SELECT' && xDOM.eq(i).children('option:selected')[0].value == '') && xDOM.eq(i).attr('data-required')
            ) {
                xDOM.eq(i).tooltip({
                    tipClass: 'tooltip-danger',
                    title: xDOM.eq(i).attr('data-tip'),
                    placement: 'top',
                    trigger: 'manual'
                });
                xDOM.eq(i).tooltip('show');
                xDOM.eq(i).on('click', function () {
                    xDOM.eq(i).tooltip('destroy');
                });
                return false;
            }
            // 格式校验
            var format = xDOM.eq(i).attr('data-format') ? parseInt(xDOM.eq(i).attr('data-format')) : '';
            if (format && xDOM.eq(i).val() && !validateRules(xDOM.eq(i).val(), format)) {
                // 弹出校验
                xDOM.eq(i).tooltip({
                    tipClass: 'tooltip-danger',
                    title: '输入内容格式错误',
                    placement: 'top',
                    trigger: 'manual'
                });
                xDOM.eq(i).tooltip('show');
                xDOM.eq(i).on('click', function () {
                    xDOM.eq(i).tooltip('destroy');
                });
                return false;
            }

            // 长度校验
            if (xDOM.eq(i).attr('maxlength') < xDOM.eq(i).val().length || xDOM.eq(i).attr('minlength') > xDOM.eq(i).val().length) {
                // 弹出校验
                xDOM.eq(i).tooltip({
                    tipClass: 'tooltip-danger',
                    title: '输入内容长度错误',
                    placement: 'top',
                    trigger: 'manual'
                });
                xDOM.eq(i).tooltip('show');
                xDOM.eq(i).on('click', function () {
                    xDOM.eq(i).tooltip('destroy');
                });
                return false;
            }
            if (name) {
                formdata[name] = xDOM.eq(i).val();
            }
            if (selectedname) {
                formdata[selectedname] = xDOM.eq(i).find("option:selected").text();
            }
        }
    }
    return formdata;
}

// 表单置空
function resetForm(xDOM) {
    $(xDOM).not(':button, :submit, :reset, :hidden, :disabled').val('').removeAttr('checked').removeAttr('selected');
}


// 检测是否登录
function checkLogin() {
    var loginResult = false;
    httpRequest({
        url: '/web/userapi/checkLogon',
        async: false,
        success: function (result, status) {
            let htmlStr = window.location.pathname.split('/')[window.location.pathname.split('/').length - 1];
            console.log(htmlStr)
            if (result.code == '200') {
                var string = '';
                if (result.data.yhxx.complete) {
                    string = '欢迎您,' + result.data.yhxx.zsxm + '<a class="gotoinfo" onclick="gotoInfo()">个人中心' + '</a>' +
                        '<a id="loginOut" onclick="loginOut()">退出登录</a>';
                } else {
                    string = '<span class="gotoinfo" onclick="gotoInfo()">' + '请先完善信息，' + '</span>' +
                        '<a id="loginOut" onclick="loginOut()">退出登录</a>';
                    if (window.location.pathname != '/mail/views/updateinfo.html') {
                        gotoInfo();
                    }
                }
                $('#searchLi').attr('data-url', './xjcxPage.html');
                $('#blpjLi').attr('data-url', './blpjPage.html');
                setTimeout(function () {

                    if ($('#searchLi').hasClass('menu-list-selected') && htmlStr != 'xjcxPage.html') {
                        $('#searchLi').trigger('click');
                    }
                    if ($('#blpjLi').hasClass('menu-list-selected') && htmlStr != 'blpjPage.html') {
                        $('#blpjLi').trigger('click');
                    }
                }, 500)
                loginResult = true;
                $('.right-login-panel').html(string);
            } else {
                console.log(window.location)
                var string = '<a id="loginBtn">登录</a>' +
                    '<a onclick="register()">注册</a>';
                $('.right-login-panel').html(string);
                $('#searchLi').attr('data-url', './searchrecord.html?type=1');
                $('#blpjLi').attr('data-url', './searchrecord.html?type=2');
                setTimeout(function () {
                    if ($('#searchLi').hasClass('menu-list-selected') && htmlStr != 'searchrecord.html') {
                        $('#searchLi').trigger('click');
                    }
                    if ($('#blpjLi').hasClass('menu-list-selected') && htmlStr != 'searchrecord.html') {
                        $('#blpjLi').trigger('click');
                    }
                }, 500)
                loginResult = false;
            }
        },
    });
    return loginResult;
}

function gotoInfo() {
    var paramsObj = getParamsObj();
    window.location.href = '/mail/views/updateinfo.html?id=' + paramsObj.id;
}

// 登录按钮
function loginIn() {
    var xDOM = $('#accountLogin input');
    var formdata = validateForm(xDOM);
    if (formdata) {
        formdata['token'] = uuid;
        if (formdata.hasOwnProperty('mm')) {
            formdata['mm'] = hex_md5(formdata['mm']);
        }
        var url = formdata.hasOwnProperty('sjhm') ? '/web/userapi/phoneLogin' : '/web/userapi/login';
        formdata["codeImg"] = formdata.hasOwnProperty('sjhm') ? formdata["codeImg-phoneLogin"] : formdata["codeImg-login"];
        httpRequest({
            url: url,
            data: formdata,
            success: function (result, status) {
                if (result.code == '200') {
                    // 登录成功
                    $.zui.store.set('user-token', result.data.token);
                    $.zui.store.set('current-page', window.location.href);
                    resetForm($('#accountLogin input'));
                    $('#loginModal').modal('hide');
                    if (result.data.isComplete) {
                        checkLogin();
                    } else {
                        var paramsObj = getParamsObj()
                        window.location.href = '/mail/views/updateinfo.html?id=' + paramsObj.id;
                    }
                } else {
                    // 登录失败 -- 修改验证码图片
                    $("#loginModal #canvas").attr('src', getYzSrc());
                }
                new $.zui.Messager(result.msg, {close: false}).show();
            }
        });
    }
}

// 账号登录按钮
function userLogin() {
    var xDOM = $('#accountLogin input');
    var formdata = validateForm(xDOM);
    if (formdata) {
        formdata['token'] = uuid;
        if (formdata.hasOwnProperty('mm')) {
            formdata['mm'] = $.base64.encode(formdata['mm']);
        }
        if (formdata.hasOwnProperty('zjhm')) {
            formdata['zjhm'] = $.base64.encode(formdata['zjhm']);
        }
        var url = formdata.hasOwnProperty('sjhm') ? '/web/userapi/phoneLogin' : '/web/auth/userapi/login';
        httpRequest({
            url: url,
            data: formdata,
            success: function (result, status) {
                if (result.code == '200') {
                    // 登录成功
                    $.zui.store.set('user-token', result.data.token);
                    $.zui.store.set('current-page', window.location.href);
                    resetForm($('#accountLogin input'));
                    $('#loginModal').modal('hide');
                    if (result.data.isComplete) {
                        checkLogin();
                    } else {
                        var paramsObj = getParamsObj()
                        window.location.href = '/mail/views/updateinfo.html?id=' + paramsObj.id;
                    }
                } else {
                    // 登录失败 -- 修改验证码图片
                    $("#loginModal #canvas").attr('src', getYzSrc());
                }
                new $.zui.Messager(result.msg, {close: false}).show();
            }
        });
    }
}

// 发送验证码
function loginSendMsg() {
    console.log(loginSendMsg)
    var sjhm = $('#accountLogin input[name="sjhm"]').val();
    var codeImg = $('#accountLogin input[name="codeImg-phonelogin"]').val();
    console.log(codeImg)
    httpRequest({
        url: '/web/userapi/sendVerifyCode',
        data: {
            sjhm: sjhm,
            codeImg: codeImg,
            action: 'phoneLogin',
            token: uuid,
        },
        success: function (result, status) {
            if (result.code == '200') {
                new $.zui.Messager('发送成功', {close: false}).show();
            } else {
                // 登录失败 -- 修改验证码图片
                $("#loginModal #canvas").attr('src', getYzSrc());
                new $.zui.Messager(result.msg, {close: false}).show();
            }
        }
    });
}

//退出登录
function loginOut() {
    httpRequest({
        url: '/web/userapi/loginout',
        success: function (result, status) {
            if (result.code == '200') {
                loginResult = true;
                var string = '<a id="loginBtn">登录</a>' +
                    '<a onclick="register()">注册</a>';
                $('.right-login-panel').html(string);
                $.zui.store.set('user-token', '');
                // tyrzlogout(result.data.sid);
            }
        }
    });
}

function tyrzlogout(sid) {
    $.ajax({
        url: 'https://oauth.hubei.gov.cn:8443/uias/uias/shotOff?sessionId=' + sid + '&jsoncallback=?',
        dataType: "jsonp",
        type: 'get',
        success: function (data) {
            if (data.success) {
                var paramsObj = getParamsObj();
                if (window.location.pathname != '/mail/views/updateinfo.html?id=' + paramsObj.id) {
                    window.location.reload();
                } else {
                    window.location.href = '/mail/views/tsqqPage.html?id=' + paramsObj.id;
                }
            } else {

                new $.zui.Messager("统一认证平台异常，需要手动退出", {
                    type: 'warning',
                    close: false,
                    time: 0,
                    actions: [{
                        name: 'close',
                        icon: 'times',
                        text: '跳转到统一认证平台',
                        action: function () {
                            window.location.href = 'zwfw.hubei.gov.cn/webview/grkj/grkj_index.html';
                        }
                    }]
                }).show();

            }
        }
    });
}


function getParamsObj() {
    var paramsObj = {};
    var params = window.location.search.substring(1, window.location.search.length).split("&");
    for (i = 0; i < params.length; i++) {
        var item = params[i].split("=");
        paramsObj[item[0]] = item[1]
    }
    return paramsObj;
}

function register() {
    if ($('registerModal').length < 1) {
        let regDom = `
		<div class="modal fade" id="registerModal">
			<div class="modal-dialog">
				<div class="modal-content">
					<div class="modal-header">
						<span class="modal-close-btn" data-dismiss="modal">×</span>
						<h4 class="modal-title" style="font-size:16px">注册须知</h4>
					</div>
					<div class="modal-body" style="display: inline-block;width: 100%">
						<div class="titleBox">
							&emsp;1.请实名注册，真实准确填写个人信息。<br>
							&emsp;2.如代他人网上信访，请使用被代理人信息进行注册。<br>
							&emsp;3.一个有效证件只能注册一次。<br>
						</div>
					</div>
					<div class="checkbox" style="margin-left: 10px;">
            		    <label>
            		      <input id="regCheck" onclick="regCheckClick()" type="checkbox">我已阅读并同意。
            		    </label>
            		</div>
					<div class="modal-footer" style="text-align: center;">
        			    <button type="button" class="btn btn-primary" id="regBtn" onclick="regAgree()">同意</button>
        			    <button type="button" class="btn btn-default" data-dismiss="modal">不同意</button>
        			</div>
				</div>
			</div>
		</div>`;
        $('body').append(regDom);
    }
    $('#regCheck').attr('checked', false);
    $('#regCheck').prop('checked', false);
    $('#regBtn').attr('disabled', true);
    $('#regBtn').addClass('disabled');
    yjjyFlag = false;
    $('#registerModal').modal({
        backdrop: 'static',
        show: true
    });
}

// 注册check监听
function regCheckClick() {
    if ($('#regCheck')[0].checked) {
        $('#regBtn').attr('disabled', false);
        $('#regBtn').removeClass('disabled');
    } else {
        $('#regBtn').attr('disabled', true);
        $('#regBtn').addClass('disabled');
    }
}

function regAgree() {
    // 注册同意弹窗
    var paramsObj = getParamsObj();
    window.location.href = "/mail/views/register.html?id=" + paramsObj.id;
}

// 初始化
function init() {
    watchWalk();
    // checkLogin();
}

function initDate() {
    var date_now = new Date();
    $("#wtfssj").datetimepicker({
        weekStart: 1,
        todayBtn: 1,
        autoclose: 1,
        todayHighlight: 1,
        startView: 2,
        minView: 2,
        forceParse: 0,
        endDate: date_now,
        format: "yyyy-mm-dd"
    });
}

//实名认证
function identityValidation(lmrlist, callbackFun) {
    httpRequest({
        needLoading: true,
        target: $("#lmrModal"),
        url: '/web/userapi/checkLmrList',
        data: {
            lmrList: JSON.stringify(lmrlist)
        },
        success: function (result, status) {
            var vaResult = false;
            if (result.code == '200') {
                vaResult = true;
            }

            if (callbackFun && typeof callbackFun == 'function') {
                callbackFun(vaResult, result.msg)
            }
        }
    });
}

function getDsljxx() {
    paramsObj = getParamsObj();

    httpRequest({
        url: '/web/complaintapi/selectDsljxxById?id=' + paramsObj.id,
        success: function (result, status) {
            if (result.code == '200') {
                var info = result.data.dsljxx;
                if (info.remark) {
                    $('#remark').html(info.remark);
                }
                sfldxx = info.sfldxx;
                let htmlStr = window.location.pathname.split('/')[window.location.pathname.split('/').length - 1];
                if (info.sfldxx) {
                    if (htmlStr == 'wyxx.html') {
                        let ldTitle = '';
                        if (paramsObj.id == '72' || paramsObj.id == '71') {
                            ldTitle = info.sxldjc;
                        } else if (paramsObj.id == '13573561') {
                            ldTitle = info.sxldjc + '领导信箱';
                        } else {
                            ldTitle = info.sxldjc.replace('信访局', '领导信箱');
                        }
                        $('#ldxxtent').text(ldTitle);
                        tsjyxx.djjgdm = info.ssjgdm;
                        tsjyxx.djjg = info.ssjgmc;
                    } else {
                        $('.sxr').hide();
                        $('#mainTitle').text(info.sxldjc);
                    }
                } else {
                    new $.zui.Messager("非法参数，页面即将关闭", {
                        type: 'warning',
                        close: false,
                        time: 0,
                        actions: [{
                            name: 'close',
                            icon: 'times',
                            text: '手动关闭',
                            action: function () {
                                closeWindow();
                            }
                        }]
                    }).show();
                    setTimeout(() => {
                        closeWindow();
                    }, 3000);
                    return;
                }
                $("#xfdjjgdm").val(info.ssjgdm);
                $("#xfdjjgmc").val(info.ssjgmc);
                var sxrList = [];
                sxrList = result.data.dsljxxLdxxList;
                $("#sxrModal .modal-body").html("");
                // if (sxrList.length <= 1) {
                //     $('input[name="sxr"]').attr('disabled', 'true');
                //     if (sxrList.length <= 1) {
                //         $('input[name="sxr"]').val(sxrList[0].sxldxm);
                //     }
                // } else {
                //     var html = "<p class='sxr-row'><span>姓名</span><span>职务</span><span>工作分工</span></p>";
                //     sxrList.forEach(function (item, index) {
                //         html += "<p class='sxr-row' data-id='" + item.ssdsljid + "' onclick='sxrClick(\"" + item.sxldxm + "\",\"" + item.ssdsljid + "\")'>"
                //             + "<span>" + item.sxldxm + "</span>"
                //             + "<span>" + item.sxldzwmc + "</span>"
                //             + "<span>" + item.fgly + "</span>"
                //             + "</p>";
                //     })
                //     $("#sxrModal .modal-body").append(html);
                // }
            } else {
                // new $.zui.Messager(result.msg,{close:false}).show();
                new $.zui.Messager(result.msg + "，页面即将关闭", {
                    type: 'warning',
                    close: false,
                    time: 0,
                    actions: [{
                        name: 'close',
                        icon: 'times',
                        text: '手动关闭',
                        action: function () {
                            closeWindow();
                        }
                    }]
                }).show();
                setTimeout(() => {
                    closeWindow();
                }, 3000);
            }
        }
    });
}

function sxrClick(name) {
    $('input[name="sxr"]').val(name);
    $('#sxrModal').modal('hide');
}

function closeWindow() {
    window.open("about:blank", "_self").close()
}

// 判断客户端还是移动端
function IsPC() {
    var userAgentInfo = navigator.userAgent;
    var Agents = ["Android", "iPhone", "SymbianOS", "Windows Phone", "iPad", "iPod"];
    var flagPc = true;
    for (var v = 0; v < Agents.length; v++) {
        if (userAgentInfo.indexOf(Agents[v]) > 0) {
            flagPc = false;
            break;
        }
    }
    return flagPc;
}

$(function () {
    init();
    /* 登录弹窗的控制 -------------------------------------------------- */
    $("body").delegate("#loginBtn", "click", function () {
        // 动态创建登录弹出层
        if ($("#loginModal").length < 1) {
            var html = '<div class="modal fade" id="loginModal">'
                + '<div class="modal-dialog">'
                + '<div class="modal-content">'
                + '<div class="modal-header">'
                + '<span class="modal-close-btn" data-dismiss="modal">×</span>'
                // + '<ul class="header-tab"><li class="tab-item active" data-id="message">短信登录</li></ul>'
                + '<ul class="header-tab"><li class="tab-item active" data-id="username">用户登录</li><li class="tab-item" data-id="message">短信登录</li></ul>'
                + '</div>'
                + '<div class="modal-body" id="accountLogin">'
                + '<div class="input-control has-icon-left user-input">'
                + '<input name="zjhm" type="text" class="form-control" data-required="true" data-tip="请输入账号" placeholder="账号">'
                + '<label class="input-control-icon-left"><i class="icon icon-user "></i></label>'
                + '</div>'
                + '<div class="input-control has-icon-left user-input">'
                + '<input name="mm" type="password" class="form-control" data-required="true" data-tip="请输入密码" placeholder="密码">'
                + '<label class="input-control-icon-left"><i class="icon icon-key"></i></label>'
                + '</div>'
                + '<div class="input-control user-input">'
                + '<input placeholder="图形验证码" name="codeImg-login" class="pin form-control user-input" data-required="true" data-tip="请输入图形验证码" maxlength="4">'
                + '<img class="user-input" id="canvas" src="" />'
                + '</div>'
                + '<button class="login-btn user-input" onclick="loginIn()">登录</button>'
                // + '<div class="user-input tyrz-block">统一认证登录</div>'
                // + '<div class="login-tip user-input" >系统登录认证服务由湖北省统一认证平台提供</div>'
                + '<div class="input-control has-icon-left message-input">'
                + '<input id="inputAccountExample3" name="sjhm" type="text" class="form-control message-input" data-required="true" data-format="2" data-tip="请输入手机号" placeholder="手机号" maxlength="20">'
                + '<label for="inputAccountExample3" class="input-control-icon-left"><i class="icon icon-phone "></i></label>'
                + '</div>'
                + '<div class="input-control">'
                + '<input placeholder="图形验证码" name="codeImg-phonelogin" class="pin form-control message-input" data-required="true" data-tip="请输入图形验证码" maxlength="4">'
                + '<img class="message-input" id="canvas" src="" />'
                + '</div>'
                + '<div class="input-control message-input">'
                + '<input placeholder="短信验证码" name="yzm" data-tip="请输入短信验证码" data-required="true" class="yzm form-control message-input" maxlength="6">'
                + '<button class="send-btn" onclick="loginSendMsg()">发送短信</button>'
                + '</div>'
                + '<button class="login-btn message-input" onclick="loginIn()">登录</button>'
                + '<p class="user-input"><span class="forgetpw-btn" onclick="forgetPwd()">忘记密码</span><span class="register-btn" onclick="register()">注册</span></p>'
                // + '<p style="text-align: center;margin:0;color: red;">提示: 老系统用户请重新注册</p>'
                + '</div></div></div></div>';
            $('body').append(html);
        }

        $('#loginModal').modal({
            backdrop: 'static',
            show: true
        })
        $("#loginModal .message-input").hide();
        $("#loginModal .user-input").show();
        $("#loginModal .tab-item").removeClass("active");
        $("#loginModal .tab-item[data-id='username']").addClass("active");
        // 初始生成图形验证码
        $("#loginModal #canvas").attr('src', getYzSrc());
    });

    // 生成图形验证码
    $("body").delegate("#loginModal #canvas", "click", function () {
        $("#loginModal #canvas").attr('src', getYzSrc());
    });
    // 统一认证
    // $("body").delegate("#loginModal .tyrz-block", "click", function () {
    //     $.zui.store.set('current-page', window.location.href);
    //     window.location.href = '/wsxf/uias_login.do?appCode=hbygxf';
    // });
    // 登录窗口tab切换
    $("body").delegate("#loginModal .tab-item", "click", function () {
        var name = $("#loginModal .tab-item.active").attr('data-id');
        if ($(this).attr('data-id') == name) {
            return;
        }
        $("#loginModal .tab-item").removeClass("active");
        $(this).addClass("active");
        $("#loginModal .user-input").toggle();
        $("#loginModal .message-input").toggle();
        $("#loginModal #canvas").attr('src', getYzSrc());
        resetForm('#loginModal input');
    });

    /* 登录弹窗的控制 end -------------------------------------------------- */
    $(".form-panel-left").height($(".form-panel-right").height());

    // createNotice();
    // getIp();

    //地址切换
    // bindChangeOrg();
});

// 点击忘记密码方法
function forgetPwd() {
    if ($('resetPwdModal').length < 1) {
        let pwdDom = `
		<div class="modal fade" id="resetPwdModal">
			<div class="modal-dialog">
				<div class="modal-content">
					<div class="modal-header">
						<span class="modal-close-btn" data-dismiss="modal">×</span>
						<h4 class="modal-title" style="font-size:16px">忘记密码</h4>
					</div>
					<div class="modal-body" style="display: inline-block;width: 100%">
						<div class="form-input form-horizontal" id="resetPwdForm">
							<div class="form-group">
								<label for="phone" class="col-sm-3 col-md-3 required">手机号码</label>
								<div class="col-sm-4 col-md-4">
									<input type="text" class="form-control" id="sjhm" placeholder="请输入手机号码" name="sjhm" data-format="2" data-required="true" data-tip="请输入手机号码">
								</div>
								<div class="yzmbtn" onclick="sendMsg('resetPwdForm')">发送验证码</div>
							</div>
							<div class="form-group">
								<label for="codeImg" class="col-sm-3 col-md-3 required">图形验证码</label>
								<div class="col-sm-4 col-md-4">
									<input placeholder="图形验证码" name="codeImg" class="pin form-control" data-required="true" data-tip="请输入图形验证码" maxlength="4">
								</div>
								<img id="canvas" src="" />
							</div>
							<div class="form-group">
								<label for="yzm" class="col-sm-3 col-md-3 required">验证码</label>
								<div class="col-sm-4 col-md-4">
									<input type="text" class="form-control" id="yzm" maxlength="6" minlength="4" placeholder="请输入验证码" name="yzm" data-required="true" data-tip="请输入验证码">
								</div>
							</div>
							<div class="form-group">
								<label for="password" class="col-sm-3 col-md-3 required">设置密码</label>
								<div class="col-sm-4 col-md-4">
									<input type="password" class="form-control" id="password" placeholder="请输入密码" name="password" data-required="true" data-tip="请输入密码">
								</div>
							</div>
							<div class="form-group">
								<label for="qrmm" class="col-sm-3 col-md-3 required">确认密码</label>
								<div class="col-sm-4 col-md-4">
									<input type="password" class="form-control" id="qrmm" placeholder="请再次输入密码确认" name="qrmm" data-required="true" data-tip="请再次输入密码确认">
								</div>
							</div>
							<div class="form-footer">
								<div class="btn submit-btn" type="button" onclick="resetPassword()">提交</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>`;
        $('body').append(pwdDom);
    }
    $('#resetPwdModal').modal({
        backdrop: 'static',
        show: true
    });
    $("#resetPwdModal #canvas").attr('src', getYzSrc());
}

function createNotice() {

    var d = new Date("2022/7/31");
    var c = new Date();
    if (d <= c) {
        return;
    }

    var c = $("#notice").length;
    if (c == 0) {
        var html =
            '<div id="notice" class="popover">' +
            '<h3 class="popover-title">通知公告</h3>' +
            '<div class="popover-content">' +
            '<p>省网上信访信息系统7月1日开展为期一个月（7月1日至7月31日）上线试运行，上线以后，阳光信访大厅及各级领导信箱改用新版。</p>' +
            '<div style="float:right;cursor:pointer;" onclick="$(\'#notice\').hide()" >关闭</div>' +
            '</div>' +
            '</div>';
        $("body").append(html);
        var h = $(document.body).height(), w = $(document.body).width(), nh = $('#notice').height(),
            nw = $('#notice').width();
        $('#notice').css("top", (h - nh - 20) + "px").css("left", (w - nw - 20) + "px").show();
    }
}

function getIp() {
    // $.post("https://app.ipdatacloud.com/v1/ip_self_search", {}, function (res) {
    //     var ipInfo = '( 您当前的IP地址: ' + res.data.ip + ', ' + res.data.province + '省-' + res.data.city + '市 )';
    //     $("fieldset legend").append("<span style='color:#004C7F' >" + ipInfo + "</span>")
    // }, "json");
}

function getNowFormatDate() {
    let date = new Date(),
        year = date.getFullYear(), //获取完整的年份(4位)
        month = date.getMonth() + 1, //获取当前月份(0-11,0代表1月)
        strDate = date.getDate() // 获取当前日(1-31)
    if (month < 10) month = `0${month}` // 如果月份是个位数，在前面补0
    if (strDate < 10) strDate = `0${strDate}` // 如果日是个位数，在前面补0

    return `${year}-${month}-${strDate}`
}


function bindChangeOrg() {

    var orgElement = '<ul>' +
        '<li><a href="/mail/szxx/tsqqPage.html?id=d2ae6a3188484b63bbf7afbec80ceacd" >新疆生产建设兵团信访局</a></li>' +
        '<li>地市州信箱</li>' +
        '<li>区县信箱</li>' +
        '</ul>';
    $('#mainTitle').append('<p id="changeOrg"><i class="icon icon-exchange"></i>切换单位</p>');
    $('#changeOrg').modalTrigger({custom: orgElement});

}