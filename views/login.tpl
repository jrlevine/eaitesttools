%rebase('eaibase.tpl', name=name)
<p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p>
<center>
%if defined('kvetch'):
    <p><font color="red">{{!kvetch}}</font></p>
%end
    <form method=post action="/login">
    <table cellpadding="3">
       <tr class="h"><th colspan="2"><p>Authorized users only</p></th></tr>
       <tr><td class="e" align=right>User:</td><td class="e"><input name=user type=text size=12 maxlength=12></td></tr>
       <tr><td class="e"
       align=right>Password:</td><td class="e"><input name=pw type=password maxlength=12 size=12></td></tr>
       <tr><td class="e" colspan=2 align=center><input type=submit value="Log In"></td></tr>
    </table>
    </form>
    <p><b>No public access to this site. All access attempts logged.</b></p>
</center>
