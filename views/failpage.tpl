%rebase('eaibase.tpl', name="Something went wrong")
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end
</center>
