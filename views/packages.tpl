%rebase('eaibase.tpl', name=name)
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end

<center>
<p>Packages to test</p>

<table rules="all" frame="border">
<tr><th class="h">ID</th>
<th class="h">Name</th>
<th class="h">Vendor</th>
<th class="h">Types</th>
<tr>

%for p in prods:
<tr class="r">
<td><a href="/package/{{p['pid']}}">*</a></td>
<td><p>{{p['name']}}</p></td>
<td><p>{{p['vendor']}}</p></td>
<td><p>{{p['types']}}</p></td>
</tr>
%end
</table>
</center>
