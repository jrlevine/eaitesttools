%rebase('eaibase.tpl', name=name)
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end

<p>Test status for {{product['name']}} {{ttype}}</p>

<p>
<table rules="all" frame="border">
<tr><th colspan="2">Pending tests</th></tr>
<th class="h">Test ID</th>
<th class="h">Summary</th>
<tr>

%for t in ndone:
<tr class="r">
<td><p><a href="/result/{{ttid}}/{{pid}}/{{t['tid']}}">{{t['testid']}}</a></p></td>
<td><p>{{t['summary']}}</p></td>
</tr>
%end
</table>
</p>

<p>
<table rules="all" frame="border">
<tr><th colspan="3">Completed tests</th></tr>
<th class="h">Test ID</th>
<th class="h">Result</th>
<th class="h">Summary</th>
<tr>

%for t in ldone:
<tr class="r">
<td><p><a href="/result/{{ttid}}/{{pid}}/{{t['tid']}}">{{t['testid']}}</a></p></td>
<td><p>{{t['status']}}</p></td>
<td><p>{{t['summary']}}</p></td>
</tr>
%end
</table>
</p>

</center>
