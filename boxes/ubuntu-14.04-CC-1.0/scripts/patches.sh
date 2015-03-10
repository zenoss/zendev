patch -d /usr/lib/python2.7/distutils -N -p2 <<EOF
Index: Lib/distutils/file_util.py
===================================================================
--- Lib/distutils/file_util.py	(revision 81651)
+++ Lib/distutils/file_util.py	(working copy)
@@ -85,7 +85,8 @@
     (os.symlink) instead of copying: set it to "hard" or "sym"; if it is
     None (the default), files are copied.  Don't set 'link' on systems that
     don't support it: 'copy_file()' doesn't check if hard or symbolic
-    linking is available.
+    linking is available. If hardlink fails, falls back to
+	_copy_file_contents()
 
     Under Mac OS, uses the native file copy function in macostools; on
     other systems, uses '_copy_file_contents()' to copy file contents.
@@ -137,24 +138,29 @@
     # (Unix only, of course, but that's the caller's responsibility)
     if link == 'hard':
         if not (os.path.exists(dst) and os.path.samefile(src, dst)):
-            os.link(src, dst)
+            try:
+                os.link(src, dst)
+                return (dst, 1)
+            except OSError:
+                pass # incase filesystem does not support hardlink
+                     # will fall through to using _copy_file_contents()
     elif link == 'sym':
         if not (os.path.exists(dst) and os.path.samefile(src, dst)):
             os.symlink(src, dst)
+            return (dst, 1)
 
     # Otherwise (non-Mac, not linking), copy the file contents and
     # (optionally) copy the times and mode.
-    else:
-        _copy_file_contents(src, dst)
-        if preserve_mode or preserve_times:
-            st = os.stat(src)
+    _copy_file_contents(src, dst)
+    if preserve_mode or preserve_times:
+        st = os.stat(src)
 
-            # According to David Ascher <da@ski.org>, utime() should be done
-            # before chmod() (at least under NT).
-            if preserve_times:
-                os.utime(dst, (st[ST_ATIME], st[ST_MTIME]))
-            if preserve_mode:
-                os.chmod(dst, S_IMODE(st[ST_MODE]))
+        # According to David Ascher <da@ski.org>, utime() should be done
+        # before chmod() (at least under NT).
+        if preserve_times:
+            os.utime(dst, (st[ST_ATIME], st[ST_MTIME]))
+        if preserve_mode:
+            os.chmod(dst, S_IMODE(st[ST_MODE]))
 
     return (dst, 1)
EOF
