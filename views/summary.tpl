%rebase('eaibase.tpl', name=name)
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end

<center>
<p>Test summary for {{ttype}}</p>

<table rules="all" frame="border" class="center">
<tr><th class="h">Test</th>
%for pname,pid in products:
  <th class="h"><a href="/package/{{pid}}">{{pname}}</a></th>
%end
<tr>

%for tname,tid in tests:
<tr class="r">
<td><p><a href="/test/{{tid}}">{{tname}}</a></p></td>
%  for pname,pid in products:
   <td><p><a href="/result/{{ttid}}/{{pid}}/{{tid}}">{{results.get(f"{pid}-{tid}","--")}}</a></p></td>
%  end
</tr>
%end
</table>

<p>Other test categories:
<form action="/summary" method="post">
{{!testerselect}}
%for tt in testtype:
| <input type=submit name=ttype value="{{tt}}">
%end
|</p>
</form>
</center>
