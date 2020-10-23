%rebase('eaibase.tpl', name=name)
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end

<center>

<form action="/newtask" method="post">
<p><table>
<tr><th class="h" colspan=2>Add a new task</th><tr>
<tr><td class="e" align=right>Tester:</td><td class="v">{{!testerselect}}</td></tr>
<tr><td class="e" align=right>Product:</td><td class="v">{{!productselect}}</td></tr>
<tr><td class="e" align=right>Type:</td><td class="v">{{!typeselect}}</td></tr>
<tr><td class="e" align=right>State:</td><td class="v">{{!stateselect}}</td></tr>
</table></p>

<p><input type=submit name=u value=Add></p>
</form>
</center>
