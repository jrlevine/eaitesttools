%rebase('eaibase.tpl', name=name)
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end
</center>

<p><em>Type:</em> {{test['testtype']}}</p>
<p><em>Summary:</em> {{test['summary']}}</p>
<p><em>Description:</em> {{test['description']}}</p>
<p><em>Action:</em> {{test['action']}}</p>
<p><em>Expected:</em> {{test['expected']}}</p>
<p><em>Class:</em> {{test['class']}}</p>

<form action="/result/{{ttid}}/{{pid}}/{{tid}}" method="post" enctype="multipart/form-data">
<input name=hv type=hidden value="{{hashval}}">
<p><table>
        <tr><th class="h" colspan=2>Results of {{test['testid']}} on {{product['name']}}</th><tr>
        <tr><td class=e>Status</td>
	  <td class=v><input name=s type=radio value="NA" {{"checked" if res and res['status']=="NA" else ""}}>NA
	  &nbsp;&nbsp;&nbsp;<input name=s type=radio value="PASS" {{"checked" if res and res['status']=="PASS" else ""}}>PASS
	  &nbsp;&nbsp;&nbsp;<input name=s type=radio value="FAIL" {{"checked" if res and res['status']=="FAIL" else ""}}>FAIL
	  &nbsp;&nbsp;&nbsp;<input name=s type=radio value="Pending" {{"checked" if res and res['status']=="Pending" else ""}}>Pending
	  </td></tr>
        <tr><td class=e>Comments</td>
	  <td class=v><textarea name=c cols=70 rows=10>{{res['comments'] if res else ""}}</textarea></td></tr>
        <tr><td class=e>Picture</td>
	  <td class=v><input name=pic type=file> (PNG or JPEG only)</td></tr>
	<tr><td class=e>&nbsp;</td>
	  <td class=v><input type=submit name=u value="Update">
	  <input type=submit name=ur value="Update/Return">
	  <input type=submit name=un value="Update/Next">
	  | <input type=submit name=rr value="Return">
	  <input type=submit name=nn value="Next"></td></tr>

        </table></p>
%if picurl:
<p><img style="border:3px solid black" src="{{!picurl}}"/></p>
%end

</form>
