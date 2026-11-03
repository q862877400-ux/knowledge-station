
const record_key = "record_data";

/**
 * 访问记录,
 * @param label 标签
 */
function saveRecord() {
  var keywords = $('meta[name="Keywords"]').attr('content');
  const record = JSON.parse(localStorage.getItem(record_key)) || [];
  var url = window.location.href;
  var index=record.findIndex(o => o.url == url);
  if (index==-1) {
    record.push({
      title:document.title,
      url:url,
      visitTime:new Date(),
      label:keywords,
      counts:1
    });
    if (record.length > 50) {
      record.shift();//移除第一个元素
    }
  }else{
    var obj=record[index];
    obj.visitTime=new Date();
    obj.counts=obj.counts+1;

    record.splice(index, 1);
    record.push(obj);
  }
  localStorage.setItem(record_key, JSON.stringify(record));
}

//获取推荐
async function getRecommendList() {
  const record = JSON.parse(localStorage.getItem(record_key)) || [];
  //let labels = record.map(obj => obj.label).join(',');
  let labels=[];
  for (let i = record.length - 1; i >= 0; i--) {
    if(record[i].label){
      var label=record[i].label.split(' ');

      for(let l of label){
        if(!labels.includes(l)){//去重
          labels.push(l);
        }
      }
    }
  }

  try {
    var host='';
    for(let j of  document.scripts){
      if(j.src.indexOf("usercenter.js")>-1){
		host=j.src.substring(0,j.src.indexOf('/UserCenter/js/usercenter.js'));
      }
    }
    let body = new FormData();
    body.append("labels",labels.join(','));
    const response = await fetch(`${host}/usapi/system/recommend`,{
      'method': 'POST',  // 请求方式
      'body': body,
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error:', error);
  }
  return null;
}



//获取互动回应
async function getInteractList() {
  const record = JSON.parse(localStorage.getItem(record_key)) || [];
  //let labels = record.map(obj => obj.label).join(',');
  let labels=[];
  for (let i = record.length - 1; i >= 0; i--) {
    if(record[i].label){
      var label=record[i].label.split(' ');

      for(let l of label){
        if(!labels.includes(l)){//去重
          labels.push(l);
        }
      }
    }
  }

  try {
    var host='';
    for(let j of  document.scripts){
      if(j.src.indexOf("usercenter.js")>-1){
        host=j.src.substring(0,j.src.indexOf('/UserCenter/js/usercenter.js'));
      }
    }
    let body = new FormData();
    body.append("labels",labels.join(','));
    const response = await fetch(`${host}/usapi/system/interact`,{
      'method': 'POST',  // 请求方式
      'body': body,
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error:', error);
  }
  return null;
}


