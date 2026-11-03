var FILE_LIST = [];
var FILE_ids = [];
var stepArr = ["yhxz", "qrxx", "xx"];
var currentStep = 1;
var agree = true;
var tsjyxx = {};
var currentWtsddm = "";
var currentZzdm = "";
var currentNrfl = "";
var currentWtfssj = "";
var regionHolderArr = ['请选择省', '请选择市/州', '请选择区/县', '请选择乡/镇', '请选择社区/街道']; //区划组件的占位提示
var nrflHolderArr = ['请选择一级内容分类', '请选择二级内容分类', '请选择三级内容分类'];
var fileList = [];
var cxuuid = '';
$(function () {
    getDsljxx();
    $('.content-wycx').hide();
    $('.content-cxjg').hide();
    getNowFormatDate();
    $(".content-tab span").click(function (e) {
        var tabName = $(e.currentTarget).find("div")[0].className;
        if (tabName == 'wyxx') {
            $('.content-wyxx').show();
            location.reload();
            $('.content-wycx').hide();
            $('.content-cxjg').hide();
        } else {
            $('.content-wycx').show();
            $('.content-wyxx').hide();
            $('.content-cxjg').hide();
            $('#cxCanvas').attr('src', getYzSrc());
        }
    });

    // 住址初始化
    getRegion(1, '130000000000', '#region');
    $('.regionSelect').hide();
    $('#region1').show();
    // 住址下拉监听事件
    $(".regionSelect , .wtfsdregionSelect").change(function () {
        var flag = $(this).hasClass('wtfsdregionSelect') ? '#wtfsdregion' : '#region';
        var index = parseInt($(this).attr('data-index'));
        var regionid = $(this).children('option:selected').val();
        if (index < 5 && regionid != '') {
            getRegion(index, regionid, flag);
        }
    });

    bindEvent();
});


function bindEvent() {
    $("#agreement").change(function (e) {
        if (agree) {
            agree = false;
            $("span,.btn").addClass("btn-disable");
        } else {
            agree = true;
            $("span,.btn").removeClass("btn-disable");
        }
    });

    $("#sendCode").click(function (e) {
        if ($(e.target).hasClass("btn-disable")) {
            return;
        }

        var sjhm = $("#sjhm").val();
        if (!(/^1[3456789]\d{9}$/.test(sjhm))) {
            toast("提示", "请输入正确的手机号码", "warning");
            return;
        }
    });


    $(".modal-dialog .sendCode").click(function (e) {
        var sjhm = $("#sjhm").val();
        var imageCode = $("#imageCode").val();
        if (!imageCode) {
            toast("提示", "请输入验证码", "warning");
            return;
        }

        $.unblockUI();
        var options = {
            block: true,
            message: "正在发送验证码..",
            url: region_root + 'userapi/sendVerifyCode',
            data: {
                sjhm: sjhm,
                action: "phoneLogin",
                codeImg: imageCode,
                token: uuid,
            },
            success: function (res) {
                if (res.code === '200') {
                    toast("提示", "发送成功", "notice");
                    var btn = $("#sendCode");
                    btn.addClass("btn-disable");
                    var i = 60;
                    btn.text(i + 's');
                    var time = setInterval(function () {
                        i--;
                        btn.text(i + 's');
                        if (i <= 0) {
                            btn.text("短信验证码");
                            btn.removeClass("btn-disable");
                            $("#imageCode").val('');
                            clearInterval(time);
                        }
                    }, 1000);
                } else {
                    toast("提示", res.msg, "warning");
                    $("#verifyImage").attr("src", $("#verifyImage").attr("src") + "?r=" + Math.random());
                }
            }
        }

        ajaxLoading(options);

    });

    $(".smscode-dialog .cancel").click(function (e) {
        $("#imageCode").val("");
        $.unblockUI();
    });

    $(".xfmd-select").change(function (e) {
        $(".wtfssj-tr").fadeIn();
        $(".sfd-tr").fadeIn();
        $(".bfyrhdw-tr").fadeOut();
        $(".bfyrzw-tr").fadeOut();
        $(".bfyrjb-tr").fadeOut();
        $(".sfss-radio-group").fadeIn();
        var obj = $(e.target);
        var xfmd = obj.val();
        if (xfmd == "01") {
            $(".wtfssj-tr").fadeOut();
            $(".sfss-radio-group").fadeOut();
            $(".sfd-tr").fadeOut();
        } else if (xfmd == "04") {
            $(".bfyrhdw-tr").fadeIn();
            $(".bfyrzw-tr").fadeIn();
            $(".bfyrjb-tr").fadeIn();
        }
    });

    $("#nr").on("input propertychange", function () {
        var $this = $(this),
            _val = $this.val(),
            count = "";
        if (_val.length > 1000) {
            $this.val(_val.substring(0, 1000));
        }
        count = $this.val().length;
        $("#text-limit").text(count + "/1000");
    });
}

function getNowFormatDate() {
    var date = new Date();
    var seperator1 = "-";
    var seperator2 = ":";
    var month = date.getMonth() + 1;
    var strDate = date.getDate();
    if (month >= 1 && month <= 9) {
        month = "0" + month;
    }
    if (strDate >= 0 && strDate <= 9) {
        strDate = "0" + strDate;
    }
    var currentdate = date.getFullYear() + seperator1 + month + seperator1 + strDate

    console.log(currentdate)
    return currentdate;
}


function next() {
    if (!agree) {
        return;
    }
    var currentSetpName = stepArr[currentStep - 1];
    $(".content-" + currentSetpName).hide();
    currentStep++;
    currentStep = currentStep < 1 ? 1 : currentStep;
    var nextSetpName = stepArr[currentStep - 1];
    $(".content-" + nextSetpName).fadeIn();
    var currentClassName = "step-" + (currentStep - 1);
    $("." + currentClassName).removeClass(currentClassName).addClass(currentClassName + "-finish");
    var nextClassName = "step-" + currentStep;
    $("." + nextClassName + "-disable").removeClass(nextClassName + "-disable").addClass(nextClassName);
    $(".content-title span").text($("." + nextClassName).text());

}

function forward() {
    if (!agree) {
        return;
    }
    var currentSetpName = stepArr[currentStep - 1];
    $(".content-" + currentSetpName).hide();
    currentStep--;
    currentStep = currentStep < 1 ? 1 : currentStep;
    var forwardSetpName = stepArr[currentStep - 1];
    $(".content-" + forwardSetpName).fadeIn();
    var currentClassName = "step-" + (currentStep + 1);
    $("." + currentClassName).removeClass(currentClassName).addClass(currentClassName + "-disable");
    var forwardClassName = "step-" + currentStep;
    $("." + forwardClassName + "-finish").removeClass(forwardClassName + "-finish").addClass(forwardClassName);
    $(".content-title span").text($("." + forwardClassName).text());

}

// 身份证校验
function idCardValid(id) {
    // 1 "验证通过!", 0 //校验不通过
    var format = /^(([1][1-5])|([2][1-3])|([3][1-7])|([4][1-6])|([5][0-4])|([6][1-5])|([7][1])|([8][1-2]))\d{4}(([1][9]\d{2})|([2]\d{3}))(([0][1-9])|([1][0-2]))(([0][1-9])|([1-2][0-9])|([3][0-1]))\d{3}[0-9xX]$/;
    //号码规则校验
    if (!format.test(id)) {
        // return { 'status': 0, 'msg': '身份证号码不合规' };
        return false;
    }
    //区位码校验
    //出生年月日校验   前正则限制起始年份为1900;
    var year = id.substr(6, 4),//身份证年
        month = id.substr(10, 2),//身份证月
        date = id.substr(12, 2),//身份证日
        time = Date.parse(month + '-' + date + '-' + year),//身份证日期时间戳date
        now_time = Date.parse(new Date()),//当前时间戳
        dates = (new Date(year, month, 0)).getDate();//身份证当月天数
    if (time > now_time || date > dates) {
        // return { 'status': 0, 'msg': '出生日期不合规' }
        return false;
    }
    //校验码判断
    var c = new Array(7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2);   //系数
    var b = new Array('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2');  //校验码对照表
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

function checkBasicInfo() {
    var zsxm = $("#zsxm").val();
    var sjhm = $("#sjhm").val();
    var sjyzm = $("#sjyzm").val();
    var zjhm = $("#zjhm").val();
    var xxzz = $("#xxzz").val();
    var zzmc = "";
    var zzmmdm = $('select[name="zzmmdm"]').val();
    var zzmmmc = $('select[name="zzmmdm"] option:selected').text();

    //姓名
    if (!zsxm) {
        new $.zui.Messager("请填写姓名", {
            type: 'warning', // 定义颜色主题
            time: 2000,
            close: false,
        }).show();
        return;
    } else if (zsxm.length === 1) {
        new $.zui.Messager("请填写完整姓名", {
            type: 'warning', // 定义颜色主题
            time: 2000,
            close: false,
        }).show();
        return;
    }

    if (!/^[\u4e00-\u9fa5]{0,}$/.test(zsxm)) {
        new $.zui.Messager("姓名只能输入中文字符", {
            type: 'warning', // 定义颜色主题
            time: 2000,
            close: false,
        }).show();
        return;
    }
    if (!zjhm) {
        new $.zui.Messager("请填写身份证号", {
            type: 'warning', // 定义颜色主题
            time: 2000,
            close: false,
        }).show();
        return;
    } else {
        if (!idCardValid(zjhm)) {
            new $.zui.Messager("身份证号格式错误", {
                type: 'warning', // 定义颜色主题
                time: 2000,
                close: false,
            }).show();
            return;
        }
    }

    if (zzmmdm == "") {
        new $.zui.Messager("请选择政治面貌", {
            type: 'warning', // 定义颜色主题
            time: 2000,
            close: false,
        }).show();
        return;
    }

    if (!(/^1[3456789]\d{9}$/.test(sjhm))) {
        new $.zui.Messager("请输入正确的手机号码", {
            type: 'warning', // 定义颜色主题
            time: 2000,
            close: false,
        }).show();
        return;
    }

    if (!sjyzm) {
        new $.zui.Messager("请填写手机验证码", {
            type: 'warning', // 定义颜色主题
            time: 2000,
            close: false,
        }).show();
        return;
    }

    var zz = $("select[name='town'] option:selected");
    if (zz.length == 0 || !$(zz).val() || $(zz).val() == -1) {
        new $.zui.Messager("住址请选择到乡、镇、区、县", {
            type: 'warning', // 定义颜色主题
            time: 2000,
            close: false,
        }).show();
        return;
    } else {
        var regionDom = $('.regionSelect');
        var regionArr = [];
        var sfdString = '';
        for (var i = 0; i < regionDom.length; i++) {
            var currentSelect = regionDom.eq(i);
            var selectedValue = currentSelect.val();
            var selectedText = currentSelect.find('option:selected').text();
            // 过滤掉空值和默认提示文本（包含"请选择"的选项）
            if (selectedValue && selectedValue != '0' && selectedValue != '-1' && !selectedText.includes('请选择')) {
                regionArr.push(selectedValue);
                sfdString += selectedText;
            }
        }
        tsjyxx.zzdm = regionArr[regionArr.length - 1];
        tsjyxx.zzmc = sfdString;
    }

    //详细住址
    if (!xxzz) {
        new $.zui.Messager("请填写详细住址", {
            type: 'warning', // 定义颜色主题
            time: 2000,
            close: false,
        }).show();
        return;
    }

    if (xxzz.length > 100) {
        new $.zui.Messager("详细住址不能超过100个字符", {
            type: 'warning', // 定义颜色主题
            time: 2000,
            close: false,
        }).show();
        return;
    }

    //手机验证码
    httpRequest({
        url: '/web/userapi/validateVerifyCode',
        data: {
            sjhm: sjhm,
            yzm: sjyzm
        },

        success: function (result, status) {
            if (result.code == '200') {
                tsjyxx.zsxm = zsxm;
                tsjyxx.sjhm = sjhm;
                tsjyxx.zjhm = zjhm;
                tsjyxx.xxzz = xxzz;
                tsjyxx.zzmmdm = zzmmdm;
                tsjyxx.zzmmmc = zzmmmc;
                checkIDCard(tsjyxx);
                // next();
                // initXx();
            } else {
                new $.zui.Messager(result.msg, {close: false}).show();
            }
        },
    });


    // var options = {
    //   block: true,
    //   message: "正在验证信息",
    //   url: region_root + 'userapi/validateVerifyCode',
    //   data: {
    //     sjhm: sjhm,
    //     yzm: sjyzm
    //   },
    //   success: function (res) {
    //     if (res.code === '200') {
    //       tsjyxx.zsxm = zsxm;
    //       tsjyxx.sjhm = sjhm;
    //       tsjyxx.zjhm = zjhm;
    //       tsjyxx.xxzz = xxzz;
    //       tsjyxx.zzdm = currentZzdm;
    //       tsjyxx.zzmc = zzmc;

    //       console.log('tsjyxxtsjyxx', tsjyxx);


    //       checkIDCard(tsjyxx);
    //     } else {
    //       toast("提示", res.msg, "warning");
    //     }
    //   }
    // }

    // ajaxLoading(options);

}


function checkIDCard(tsjyxx) {
    httpRequest({
        url: '/web/userapi/validateIDCard',
        data: {
            zjhm: tsjyxx.zjhm,
            xm: tsjyxx.zsxm
        },
        success: function (result, status) {
            if (result.code == '200') {
                next();
                initXx();
            } else {
                new $.zui.Messager(result.msg, {close: false}).show();
            }
        },
    });
}

var saveOptions = {};

function finish() {
    saveOptions = {};
    var wdbt = $("#wdbt").val();
    if (!wdbt) {
        new $.zui.Messager('请填写信件标题', {close: false}).show();
        return;
    } else {
        tsjyxx.wdbt = wdbt;
    }

    var xfmd = $("#xfmd option:selected").text(), xfmddm = $("#xfmd option:selected").val();
    tsjyxx.xfmd = xfmd;
    tsjyxx.xfmddm = xfmddm;
    if (xfmddm == "04") {
        var bfyrhdw = $("#bfyrhdw").val();
        var pattern = /^[\u0391-\uFFE5A-Za-z\.]+$/;
        var validate = /^[\u0391-\uFFE5]+$/;
        if (!bfyrhdw) {
            new $.zui.Messager('请填写被反映人单位', {close: false}).show();

            return;
        } else {
            if (!pattern.test(bfyrhdw)) {
                new $.zui.Messager('被反映人单位必须为汉字、字母或', {close: false}).show();
                return;
            }
            if ($("#bfyrzw").val() != '') {
                if (!validate.test($("#bfyrzw").val())) {
                    new $.zui.Messager('被反映人职位必须为汉字', {close: false}).show();
                    return;
                }
            }
            tsjyxx.bfyrhdw = bfyrhdw;
            tsjyxx.bfyrzw = $("#bfyrzw").val();
            tsjyxx.bfyrjbmc = $("select[class='bfyrjb-select'] option:selected").text();
            tsjyxx.bfyrjbdm = $("select[class='bfyrjb-select'] option:selected").val();
        }
    } else {
        tsjyxx.bfyrhdw = null;
        tsjyxx.bfyrzw = null;
        tsjyxx.bfyrjbmc = null;
        tsjyxx.bfyrjbdm = null;
    }

    if (xfmddm != "01") {
        //问题发生时间
        if (!currentWtfssj) {
            new $.zui.Messager('请选择问题发生时间', {close: false}).show();
            return;
        } else {
            tsjyxx.wtfssj = currentWtfssj;
        }
        var sfd = $("select[name='town'] option:selected");
        if (sfd.length == 0 || !$(sfd).val() || $(sfd).val() == -1) {
            new $.zui.Messager("住址请选择到乡、镇、区、县", {
                type: 'warning', // 定义颜色主题
                time: 2000,
                close: false,
            }).show();
            return;
        } else {
            var regionDom = $('.wtfsdregionSelect');
            var regionArr = [];
            var sfdString = '';
            for (var i = 0; i < regionDom.length; i++) {
                if (regionDom.eq(i).val() != '') {
                    regionArr.push(regionDom.eq(i).val());
                    sfdString += regionDom.eq(i).find('option:selected').text();
                }
            }
            currentWtsddm = regionArr[regionArr.length - 1];
            var sfdmc = sfdString;
        }

        tsjyxx.sfddm = currentWtsddm;
        tsjyxx.sfd = sfdmc;

        var sfdxq = $("#sfdxq").val();
        if (!sfdxq) {
            new $.zui.Messager('请填写问题发生地', {close: false}).show();
            return;
        } else {
            tsjyxx.sfdxq = sfdxq;
        }

    }

    // 内容分类
    var nrfldm = $("select[name='nrfl3'] option:selected").val();
    var hasChildren = $("select option[value='" + currentNrfl + "']").attr("data-child");

    if (nrfldm == '-1' || nrfldm.length != 6 || nrfldm.substring(4) == '00') {
        new $.zui.Messager('请补全问题分类', {close: false}).show();
        return;
    } else {
        let nrflDom = $(".nrflSelect");
        let nrflArr = [];
        let nrflString = '';
        for (var i = 0; i < nrflDom.length; i++) {
            if (nrflDom.eq(i).val() != '' && nrflDom.eq(i).val() != 0) {
                nrflArr.push(nrflDom.eq(i).val());
                nrflString += ((i == 0 ? '' : '/') + nrflDom.eq(i).find("option:selected").text());
            }
        }

        tsjyxx.wtlb = nrflString;
        tsjyxx.wtlbdm = nrflArr[nrflArr.length - 1];
        ;
    }


    //信件内容
    var nr = $("#nr").val();
    if (!nr) {
        new $.zui.Messager('请填写信件内容', {close: false}).show();

        return;
    } else {
        tsjyxx.nr = nr;
    }

    tsjyxx.fjjson = JSON.stringify(FILE_ids);
    tsjyxx.sxr = $("#sxrName").text();
    let isldxxmc = $("#ldxxtent").text();
    if (isldxxmc.includes('局长信箱')) {
        tsjyxx.xfxs = '601';
    } else if (isldxxmc.includes('领导信箱')) {
        tsjyxx.xfxs = '600';
    }
    httpRequest({
        url: '/web/complaintapi/saveLdxx',
        data: tsjyxx,
        success: function (result, status) {
            if (result.code == '200') {
                $('#searchCode').text(result.data.searchCode);
                $('#cxmModal').modal({backdrop: 'static', show: true,});
                console.log('tsjyxxtsjyxx', result);
            } else {
                new $.zui.Messager(result.msg, {close: false}).show();
            }
        },
    });

}


// 获取问题发生地各级别的下拉选项
function getRegion(index, regionid, flag) {
    httpRequest({
        url: '/web/commonapi/getRegionByPid?pid=' + regionid,
        success: function (result, status) {
            if (result.code == '200' && index < 5) {
                var idname = flag + (index + 1);
                var html = '<option value="">' + regionHolderArr[index] + '</option>';
                result.data.regions.forEach(function (item, index) {
                    html +=
                        '<option value="' + item.value + '">' + item.text + '</option>';
                });
                $(idname).html(html);
                $(idname).fadeIn();
            } else {
                new $.zui.Messager(result.msg, {close: false}).show();
            }
        },
    });
}

function modifYzm() {
    var sjhm = $("#sjhm").val();
    if (!sjhm) {
        new $.zui.Messager('请输入手机号码', {close: false}).show();
        return;
    }
    $('#sendMsgModal').modal({backdrop: 'static', show: true,});
    $('#sendMsgModal #canvas').attr('src', getYzSrc());
}

// 获取验证图片src
function getYzSrc() {
    let yzmuuid = guid();
    cxuuid = yzmuuid;

    var url = '/wsxf/web/userapi/verifyImage?token=' + yzmuuid;
    return url;
}


function submityzm() {
    var sjhm = $("#sjhm").val();
    var imageCode = $("#codeImg").val();
    if (!imageCode) {
        new $.zui.Messager('请输入验证码', {close: false}).show();
        return;
    }
    ;
    httpRequest({
        url: '/web/userapi/sendVerifyCode',
        data: {
            sjhm: sjhm,
            codeImg: imageCode,
            action: "phoneLogin",
            token: cxuuid,
        },
        success: function (result, status) {
            if (result.code == '200') {
                new $.zui.Messager('发送成功', {close: false}).show();
                $('#sendMsgModal').modal('hide');
                var btn = $("#yzmCodebtn");
                btn.addClass("yzmbtn-disable");
                var i = 60;
                btn.text(i + 's后再发送');
                var time = setInterval(function () {
                    i--;
                    btn.text(i + 's后再发送');
                    if (i <= 0) {
                        btn.text("短信验证码");
                        btn.removeClass("yzmbtn-disable");
                        $("#codeImg").val('');
                        clearInterval(time);
                    }
                }, 1000);
            } else {
                $('#canvas').attr('src', getYzSrc());
                new $.zui.Messager(result.msg, {close: false}).show();
            }
        },
    });
}


// 我要写信

// 初始化写信页面
function initXx() {
    $('.bfyr').hide();
    $('#wtfssj').val(getNowFormatDate())
    currentWtfssj = getNowFormatDate();
    // 住址初始化
    $('.wtfsdregionSelect').hide();
    $('#wtfsdregion1').show();

    getRegion(1, '130000000000', '#wtfsdregion');

    //内容分类初始化
    getNrflData(0, '1');
    $(".nrflSelect").hide();
    $("#nrfl1").show();
    // 内容分类下拉监听
    $(".nrflSelect").change(function () {
        var index = parseInt($(this).attr('data-index'));
        var nrflid = $(this).children('option:selected').val();
        let parentid = $(this).children('option:selected').attr('parentid');
        for (var i = index; i < 3; i++) {
            $('#nrfl' + (i + 1)).fadeOut();
        }
        if (index < 3 && nrflid != '') {
            getNrflData(index, parentid);
        }
    })


    // 文件组件初始化选项
    var uploadOptions = {
        chunk_size: 0,
        url: '/wsxf/ldxx/commonapi/fileUpload',
        autoUpload: true, // 自动上传
        headers: {
            'user-token': $.zui.store.get('user-token')
                ? $.zui.store.get('user-token')
                : '',
        },
        limitFilesCount: 5,
        filters: {
            mime_types: [
                {title: '图片', extensions: 'jpg,jpeg,png,bmp'},
                {title: '文件', extensions: 'doc,docx,txt,pdf'},
            ],
            //最大上传文件为 10MB
            max_file_size: '10mb',
            // 不允许上传重复文件
            prevent_duplicates: true,
        },
        deleteActionOnDone: function (file, doRemoveFile) {
            let id = file.remoteData.data.recordid;
            fileList.forEach(function (item, index) {
                if (item == id) {
                    fileList.splice(index, 1);
                }
            });
            return true;
        },
        responseHandler: function (responseObject, file) {
            var result = new Object();
            result = JSON.parse(responseObject.response);
            if (result.code != '200') {
                return result.msg;
            } else {
                fileList.push(result.data.recordid);
            }
        },
    };
    $('#tableUploader').uploader(uploadOptions);
}


$('#xfmd').change(function () {
    var xfmd = $(this).children('option:selected').val();
    if (xfmd == '04') {
        $('.bfyr').show();
    } else if (xfmd == '01') {
        $('.isyjjy').hide();
        $('.bfyr').hide();
    } else {
        $('.bfyr').hide();
        $('.isyjjy').show();
    }
    $('.form-panel-left').height($('.form-panel-right').height());
});

// 获取内容分类下拉选项
function getNrflData(index, parentid) {
    if (index != 0 && parentid == '') {
        return
    }
    httpRequest({
        url: '/web/commonapi/getNrflByPid?pid=' + parentid,
        success: function (result, status) {
            if (result.code == '200' && index < 3) {
                var idname = '#nrfl' + (index + 1);
                var html = '<option parentid="" value="">' + nrflHolderArr[index] + '</option>';
                result.data.nrfls.forEach(function (item) {
                    html += '<option parentid="' + item.parent + '" value="' + item.value + '">' + item.text + '</option>';
                })
                $(idname).html(html);
                $(idname).fadeIn();
            } else {
                new $.zui.Messager(result.msg, {close: false}).show();
            }
        }
    });
}

$("#canvas").on("click", function () {
    $("#canvas").attr('src', getYzSrc());
});


$(".cxmbtn").on("click", function () {
    $('#cxmModal').modal('hide');
    location.reload();
});

// 我要查询
function submitCXM() {
    var cxxm = $("#cxxm").val();
    var cxm = $("#cxm").val();
    var cxcodeImg = $("#cxcodeImg").val();
    if (!cxxm) {
        new $.zui.Messager('请填写姓名', {close: false}).show();
        return;
    }
    if (!cxm) {
        new $.zui.Messager('请填写查询码', {close: false}).show();
        return;
    }
    if (!cxcodeImg) {
        new $.zui.Messager('请填写图形验证码', {close: false}).show();
        return;
    }
    var obj = getParamsObj();
    let area = 'ldxx';
    if (obj.id == 71) {
        area = 'szxx'
    } else if (obj.id == 72) {
        area = 'jzxx'
    }
    httpRequest({
        url: '/web/complaintapi/getLdxx',
        data: {
            zsxm: cxxm,
            cxm: cxm,
            codeImg: cxcodeImg,
            token: cxuuid,
            area: area
        },
        success: function (result, status) {
            if (result.code == '200') {
                $('.content-wycx').hide();
                var paramsObj = result.data.tsjyxx;
                //获取信件信息
                httpRequest({
                    url: '/web/complaintapi/getTsjyxx?recordid=' + paramsObj.recordid,
                    success: function (result, status, xhr) {
                        if (result.code == '200') {
                            info = result.data.tsjyxx;
                            var html = '信访日期：' + info.xfrqDisplay + '<br>' +
                                '信访目的：' + info.xfmd + '<br>';

                            if (info.tsjylx == "0") {
                                html += '问题发生时间：' + info.wtfssjDisplay + '<br>' +
                                    '问题发生地：' + info.sfd + '<br>' +
                                    '联名人数：' + (info.xfrs - 1) + '<br>' +
                                    '投诉内容：' + (info.tsnr);
                            }

                            $('.xfjxx-bar').html(html);

                            //获取办理状态
                            httpRequest({
                                url: '/web/complaintapi/getBlfsxxList?tsjyxxid=' + paramsObj.recordid,
                                success: function (result, status, xhr) {
                                    if (result.code == '200') {
                                        var blfsxxList = result.data.blfsxxList;
                                        var html = '';

                                        if (blfsxxList.length > 0) {
                                            blfsxxList = blfsxxList.reverse();
                                            blfsxxList.forEach(function (item, index) {
                                                if (item.hasOwnProperty('qxjg') && item.qxjg) {
                                                    html += '<li class="blqk-item">' +
                                                        '<span class="date">' + item.blsjDisplay + '</span>' +
                                                        '<p>由' + item.bljg + '<span class="">' + item.blfs + '至</span>' + item.qxjg + '</p>' +
                                                        '</li>'
                                                    if (index == 0) {
                                                        $('.blqkStr').text('由' + item.bljg + item.blfs + '至' + item.qxjg);
                                                    }
                                                } else {
                                                    var gznr = item.gznr ? '<p>告知内容：' + item.gznr + '</p>' : "";
                                                    html += '<li class="blqk-item" id="' + item.groupid + '">' +
                                                        '<span class="date">' + item.blsjDisplay + '</span>' +
                                                        '<p>由' + item.bljg + '<span class="">出具' + item.blfs + '</span></p>' +
                                                        gznr +
                                                        '</li>';

                                                    if (index == 0) {
                                                        $('.blqkStr').text('由' + item.bljg + '出具' + item.blfs);
                                                    }
                                                }
                                            })
                                            $('.blqk-bar-list').html(html);
                                        } else {
                                            var wdbt = info.wdbt ? info.wdbt : "事项";
                                            if (info.blzt != 2) {
                                                $('.blqk-panel').hide();
                                                $('.tsjStr').text('您于' + info.xfrqDisplay + '反映的' + wdbt + '已提交，我们会尽快办理。');
                                            } else {
                                                $('.tsjStr').text('您于' + info.xfrqDisplay + '反映的' + wdbt + '已办结。');
                                            }
                                        }
                                    }
                                }
                            });
                        }
                    }
                });


                httpRequest({
                    url: '/web/complaintapi/getMydpj?tsjyxxid=' + paramsObj.recordid,
                    success: function (result, status, xhr) {
                        if (result.code == '200') {
                            var mydxx = result.data.mydpjxx;
                            // mydxx为null或者两个二zt均为0则不展示
                            // pjzt 0-不能 1-可以 2-已评价 3-超期未评
                            if (mydxx) {
                                //信访部门
                                if (mydxx.xfbmpjzt == 0) {
                                    $('.xfbm-bar').hide();
                                } else if (mydxx.xfbmpjzt == 2 && mydxx.zrdwpjzt == 1) {
                                    $('input:radio.xfbmpj[value=' + mydxx.xfbmmyz + ']').attr("checked", 'checked');
                                    if (mydxx.xfbmpjnr) {
                                        $('.xfbm-bar textarea').html(mydxx.xfbmpjnr);
                                    }
                                } else if (mydxx.xfbmpjzt == 2 || mydxx.xfbmpjzt == 3) {
                                    $('.xfbm-bar').show();
                                    $('.xfbm-bar input').attr("disabled", "disabled");
                                    $('.xfbm-bar textarea').attr("disabled", "disabled");
                                    $('.xfbm-bar textarea').hide();
                                    $('.xfbm-bar .xfbmpj').remove();
                                    if (mydxx.xfbmpjzt == 2) {
                                        if (mydxx.xfbmpjnr) {
                                            $('.xfbm-bar .ypjnr').html('评价内容：' + mydxx.xfbmpjnr);
                                        }
                                        $('.xfbm-bar .ypjmyz').html('服务评价：' + (mydxx.xfbmmyz == 0 ? '满意' : mydxx.xfbmmyz == 1 ? '基本满意' : '不满意'));
                                    }
                                } else {
                                    $('input:radio.xfbmpj[value=0]').attr("checked", 'checked');
                                }
                                // $('input:radio.xfbmpj[value='+mydxx.xfbmmyz+']').attr("checked",'checked');
                                //责任单位
                                if (mydxx.zrdwpjzt == 0) {
                                    $('.zrdw-bar').hide();
                                } else if (mydxx.zrdwpjzt == 2 || mydxx.zrdwpjzt == 3) {
                                    $('.zrdw-bar').show();
                                    $('.zrdw-bar input').attr("disabled", "disabled");
                                    $('.zrdw-bar textarea').attr("disabled", "disabled");
                                    $('.zrdw-bar textarea').hide();
                                    $('.zrdw-bar .zrdwmpj').remove();
                                    if (mydxx.zrdwpjzt == 2) {
                                        if (mydxx.zrdwpjnr) {
                                            $('.zrdw-bar .ypjnr').html('评价内容：' + mydxx.zrdwpjnr);
                                        }
                                        $('.zrdw-bar .ypjmyz').html('服务评价：' + (mydxx.zrdwmyz == 0 ? '满意' : mydxx.zrdwmyz == 1 ? '基本满意' : '不满意'));
                                    }
                                } else {
                                    $('input:radio.zrdwmpj[value=0]').attr("checked", 'checked');
                                }

                                if (mydxx.xfbmpjzt == 1 || mydxx.zrdwpjzt == 1) {
                                    $('.submitPj').show();
                                } else {
                                    $('.submitPj').hide();
                                }
                            } else {
                                $('.mydpj-panel').hide();
                            }
                        } else {

                        }
                    }
                });


                $('.content-cxjg').show();

                // new $.zui.Messager('发送成功', { close: false }).show();
            } else {
                new $.zui.Messager(result.msg, {close: false}).show();
            }
        },
    });
};

$("#cxCanvas").on("click", function () {
    $("#cxCanvas").attr('src', getYzSrc());
});

function submitMydpj(){
    var formdata = validateForm($('.mydpj-panel .form-control'));
    formdata['xfbmmyz'] = $('input[name="xfbmpj"]:checked').val();
    formdata['zrdwmyz'] = $('input[name="zrdwmpj"]:checked').val();
    if(formdata['xfbmmyz'] == '3' && !formdata.xfbmpjnr) {
        $("textarea[name='xfbmpjnr']").focus();
        new $.zui.Messager('请填写您不满意的理由，督促我们更好的改进工作',{close:false}).show();
        return false;
    }
    if(formdata['zrdwmyz'] == '3' && !formdata.zrdwpjnr) {
        $("textarea[name='zrdwpjnr']").focus();
        new $.zui.Messager('请填写您不满意的理由，督促我们更好的改进工作',{close:false}).show();
        return false;
    }
    formdata['tsjyxxid'] = info.recordid;
    httpRequest({
        url: '/web/complaintapi/saveMydpj',
        data: formdata,
        success:function(result, status, xhr){
            new $.zui.Messager(result.msg,{close:false}).show();
            if(result.code == '200') {
                setTimeout(function(){
                    window.location.reload();
                },2000)
            }
        }
    });
}




