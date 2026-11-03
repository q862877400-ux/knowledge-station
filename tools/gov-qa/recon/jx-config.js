var defaultConfig = {
  nopic: '/default/common/images/nopic.png', //无图替换图片
  pageSize: $("#pageSize").val() || 15, //每页条数
  addHdFilesPath: { //互动附件/图片补充路径（互动交流与内容中心文件分开存储）
    mail: '/icsMail',
    question: '/icsQuestion',
    collect: '/icsCollect',
    // interview: '/icsInterview',
    interview: ''
  },
  statusCode: { //调查、问卷、访谈状态码
    601: '未开始',
    602: '进行中',
    603: '已结束'
  },
  userIdObj: {
    // tenantId:租户id;
    // deptId:部门id;  
    // qdId:渠道id ; 
    // siteId:站点id
    tenantId: '1749973237782081536',
    deptId:'1750348077562798080',
    siteId:'1750350048251023360',
    qdId: '1751807511324454912',
  },
}

var ajaxUrl = { //接口路径
  base: '',
  sr: { //数融接口
    webSearch: {
      queryList: "/queryList", //分页查询
      getManuscriptById: "/getManuscriptById", //通过id查询稿件
      searchManuscript: "/searchManuscript", //通过栏目id或稿件正文或稿件标题查询当前栏目下的稿件或当前栏目及子集
    },
    hd: { //数融互动接口
      mail: { //信箱
        list: '/api/mail/list', // 获取信件列表
        detail: ' /api/mail/detail', // 获取信件详情
        add: '/api/mail/add', //添加信件
        queryMailStatistics: '/api/mail/queryMailStatistics' //获取信件统计接口
      },
      question: { //调查
        list: '/api/question/list', // 获取问卷列表 
        detail: '/api/question/detail', // 获取详情
        stats: '/api/question/stats', // 获取详情
        add: '/api/question/answer/add', // 添加问卷
        record: '/api/question/record', //获取问卷填空题回答列表
        queryControllerSurvey: '/api/question/queryControllerSurvey', //通过站点id或者部门id获取征集调查数据
      },
      collect: { //征集
        list: '/api/collect/list', // 获取列表
        detail: ' /api/collect/detail', // 获取详情
        opinion: '/api/collect/opinion', //获取征集留言列表
        add: ' /api/collect/opinion/add', //添加征集留言
      },
      interview: { //访谈
        list: '/api/interview/list', //获取访谈列表
        detail: ' /api/interview/detail', // 获取详情
        transcriptList: '/api/interview/transcript/list', //获取访谈实录列表
        messageList: '/api/interview/message/list/', //获取访谈留言列表 
        messageListHighlight: '/api/interview/message/list/highlight', //集锦留言
        addMessage: '/api/interview/message/add', //添加访谈留言
      },
      captcha: '/api/captcha/getimg' //验证码
    }
  },
  custom: { //定制开发接口
    searchList: '/u/search/list/', //搜索列表
  }
}


//省政府部门聚合部门文件栏目匹配站点代号-机构职能稿件匹配
var aggregationWebsiteCod =[
    {
        websiteCod:'jxsfzhggwyh',
        domain:'http://drc.jiangxi.gov.cn',
        websiteName:'省发展改革委'
    },
    {
        websiteCod:'jxjyw',
        domain:'http://jyt.jiangxi.gov.cn',
        websiteName:'省教育厅'
    },
    {
        websiteCod:'jxskxjst',
        domain:'http://kjt.jiangxi.gov.cn',
        websiteName:'省科学技术厅'
    },
    {
        websiteCod:'jxsgyhxxht',
        domain:'http://gxt.jiangxi.gov.cn',
        websiteName:'省工业和信息化厅'
    },
    {
        websiteCod:'jxsgat',
        domain:'http://gat.jiangxi.gov.cn',
        websiteName:'省公安厅'
    },
    {
        websiteCod:'jxsmzt',
        domain:'http://mzt.jiangxi.gov.cn',
        websiteName:'省民政厅'
    },
    {
        websiteCod:'jxssft',
        domain:'http://sf.jiangxi.gov.cn',
        websiteName:'省司法厅'
    },
    {
        websiteCod:'jxsczt',
        domain:'http://jxf.jiangxi.gov.cn',
        websiteName:'省财政厅'
    },
    {
        websiteCod:'jxsrlzyhshbzt',
        domain:'http://rst.jiangxi.gov.cn',
        websiteName:'省人力资源和社会保障厅'
    },
    {
        websiteCod:'jxszrzyt',
        domain:'http://bnr.jiangxi.gov.cn',
        websiteName:'省自然资源厅'
    },
    {
        websiteCod:'jxssthjt',
        domain:'http://sthjt.jiangxi.gov.cn',
        websiteName:'省生态环境厅'
    },
    {
        websiteCod:'jxszfhcxjst',
        domain:'http://zjt.jiangxi.gov.cn',
        websiteName:'省住房城乡建设厅'
    },
    {
        websiteCod:'jxsjtyst',
        domain:'http://jt.jiangxi.gov.cn',
        websiteName:'省交通运输厅'
    },
    {
        websiteCod:'jxsslt',
        domain:'http://slt.jiangxi.gov.cn',
        websiteName:'省水利厅'
    },
    {
        websiteCod:'jxsnynct',
        domain:'http://nync.jiangxi.gov.cn',
        websiteName:'省农业农村厅'
    },
    {
        websiteCod:'jxsswt',
        domain:'http://swt.jiangxi.gov.cn',
        websiteName:'省商务厅'
    },
    {
        websiteCod:'jxswhhlyt',
        domain:'http://dct.jiangxi.gov.cn',
        websiteName:'省文化和旅游厅'
    },
    {
        websiteCod:'jxswsjkwyh',
        domain:'http://hc.jiangxi.gov.cn',
        websiteName:'省卫生健康委员会'
    },
    {
        websiteCod:'jxstyjrswt',
        domain:'https://tyjrswt.jiangxi.gov.cn',
        websiteName:'省退役军人事务厅'
    },
    {
        websiteCod:'jxsyjglt',
        domain:'http://yjglt.jiangxi.gov.cn',
        websiteName:'省应急厅'
    },
    {
        websiteCod:'jxssjt',
        domain:'http://audit.jiangxi.gov.cn',
        websiteName:'省审计厅'
    },
    {
        websiteCod:'jxsrmzfwsbgs',
        domain:'http://jxwb.jiangxi.gov.cn',
        websiteName:'省外办'
    },
    {
        websiteCod:'jxsgzw',
        domain:'http://gzw.jiangxi.gov.cn',
        websiteName:'省国资委'
    },
    {
        websiteCod:'jxslyj',
        domain:'http://ly.jiangxi.gov.cn',
        websiteName:'省林业局'
    },
    {
        websiteCod:'amr',
        domain:'http://amr.jiangxi.gov.cn',
        websiteName:'省市场监督管理局'
    },
    {
        websiteCod:'jxsgbdsj',
        domain:'http://gdj.jiangxi.gov.cn',
        websiteName:'省广播电视局'
    },
    {
        websiteCod:'jxsmzzjswj',
        domain:'http://mzj.jiangxi.gov.cn',
        websiteName:'省民宗局'
    },
    {
        websiteCod:'jxstyj',
        domain:'http://tyj.jiangxi.gov.cn',
        websiteName:'省体育局'
    },
    {
        websiteCod:'jxstjj',
        domain:'http://tjj.jiangxi.gov.cn',
        websiteName:'省统计局'
    },
    {
        websiteCod:'jxsgfdybgs',
        domain:'http://rf.jiangxi.gov.cn',
        websiteName:'省国防动员办'
    },
    {
        websiteCod:'jxsylbzj',
        domain:'http://ybj.jiangxi.gov.cn',
        websiteName:'省医保局'
    },
    {
        websiteCod:'jxsjgswglj',
        domain:'http://sgj.jiangxi.gov.cn',
        websiteName:'省管局（机关事务管理局）'
    },
    {
        websiteCod:'jxslshwzcbj',
        domain:'http://lswz.jiangxi.gov.cn',
        websiteName:'省粮食储备局'
    },
    {
        websiteCod:'jxsypjdglj',
        domain:'http://mpa.jiangxi.gov.cn',
        websiteName:'省药监局'
    },
    {
        websiteCod:'jxszfbzhgjjglzx',
        domain:'http://www.jxzfgjj.cn',
        websiteName:'江西省住房保障和公积金管理中心'
    }
] 

//获取地址参数
function getParams(name) {
  var reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)')
  var r = window.location.search.substr(1).match(reg)
  if (r != null) return decodeURI(r[2])
  return null
}

function getDept(data, val) {
	var metadataValue = '-';
	$.each(data, function(i, n) {
		if(n.name == val || n.metadataId == val) {
			metadataValue = n.metadataValue;
		}
	});
	return metadataValue;
}
