%rebase('eaibase.tpl', name=name)
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end

<center>
<p>No tests resutlts for {{ttype}}</p>

<p>Other test categories:
<form action="/summary" method="post">
{{!testerselect}}
%for tt in testtype:
| <input type=submit name=ttype value="{{tt}}">
%end
|</p>
</form>
</center>
