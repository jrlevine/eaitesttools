%rebase('eaibase.tpl', name=name)
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end

<center>
<p>Tasks to do</p>

<table rules="all" frame="border">
<tr><th class="h">Taek</th>
<th class="h"><a href="/tasks/user">Tester</a></th>
<th class="h"><a href="/tasks/product">Product</a></th>
<th class="h"><a href="/tasks/testtype">Type</a></th>
<th class="h"><a href="/tasks/state">State</a></th>
<th class="h">Ntests</th>
<th class="h">Ndone</th>
<th class="h">Nleft</th>
<tr>

%for t in tasks:
<tr class="r">
<td><a href="/task/{{t['ttid']}}/{{t['pid']}}/{{t['testtype']}}">*</a></td>
<td><p>{{t['user']}}</p></td>
<td><p><a href="/package/{{t['pid']}}">{{t['product']}}</a></p></td>
<td><p>{{t['testtype']}}</p></td>
<td><p>{{t['state']}}</p></td>
<td><p>{{t['ntests']}}</p></td>
<td><p>{{"" if t['ndone'] is None else t['ndone'] }}</p></td>
%if t['nleft'] is None:
<td><p>&nbsp;</p></td>
%elif t['nleft'] == 0:
<td><p><a href="/finish/{{t['ttid']}}/{{t['pid']}}/{{t['testtype']}}/Done">0</a></p></td>
%else:
<td><p><a href="/finish/{{t['ttid']}}/{{t['pid']}}/{{t['testtype']}}/Working">{{t['nleft']}}</a></p></td>
%end
</tr>
%end
</table>

<p><a href="/newtask">New Task</a></p>

</center>
