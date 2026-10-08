"use strict";function getDocListByApi(t,a){$.ajax({method:"POST",url:RequestBasic+"/public/email/paginate",data:JSON.stringify(t),contentType:"application/json;",dataType:"json",headers:{"Content-Type":"application/json",Authorization:accessToken},success:function(t){a(t)}})}
//# sourceMappingURL=api.min.js.map
