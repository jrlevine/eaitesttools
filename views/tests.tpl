%rebase('eaibase.tpl', name=name)
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end

<center>
<p>|
%for tt in testtype:
<a href="/tests/{{tt}}">{{tt}}</a> |
%end
</p>

<p>Test descriptions for {{ttype}}</p>

<table rules="all" frame="border">
<tr><th class="h">Test ID</th>
<th class="h">Type</th>
<th class="h">Summary</th>
<th class="h">Class</th>
<tr>

%for t in tests:
<tr class="r">
<td><p><a href="/test/{{t['tid']}}">{{t['testid']}}</a></p></td>
<td><p>{{t['testtype']}}</p></td>
<td><p>{{t['summary']}}</p></td>
<td><p>{{t['class']}}</p></td>
</tr>
%end
</table>

</center>
