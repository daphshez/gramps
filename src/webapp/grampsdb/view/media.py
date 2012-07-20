# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2009         Douglas S. Blank <doug.blank@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# $Id: utils.py 19637 2012-05-24 17:22:14Z dsblank $
#

""" Views for Person, Name, and Surname """

## Gramps Modules
from webapp.utils import _, boolean, update_last_changed, build_search
from webapp.grampsdb.models import Media
from webapp.grampsdb.forms import *
from webapp.libdjango import DjangoInterface
from gen.config import config 

## Django Modules
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import Context, RequestContext
from django.http import HttpResponse

## Other Python Modules
from PIL import Image
NEW_PIL = [int(i) for i in Image.VERSION.split(".")] >= [1, 1, 7]
if not NEW_PIL:
    import png
import os

## Globals
dji = DjangoInterface()

def pb2image(pb):
    width, height = pb.get_width(), pb.get_height()
    return Image.fromstring("RGB", (width,height), pb.get_pixels())
 
def process_media(request, context, handle, action, add_to=None): # view, edit, save
    """
    Process action on person. Can return a redirect.
    """
    context["tview"] = _("Media")
    context["tviews"] = _("Media")
    context["action"] = "view"
    view_template = "view_media_detail.html"
    
    if handle == "add":
        action = "add"
    if request.POST.has_key("action"):
        action = request.POST.get("action")

    # Handle: edit, view, add, create, save, delete, share, save-share
    if action == "share":
        item, handle = add_to
        context["pickform"] = PickForm("Pick media", 
                                       Media, 
                                       (),
                                       request.POST)     
        context["object_handle"] = handle
        context["object_type"] = item
        return render_to_response("pick.html", context)
    elif action == "save-share":
        item, handle = add_to 
        pickform = PickForm("Pick media", 
                            Media, 
                            (),
                            request.POST)
        if pickform.data["picklist"]:
            parent_model = dji.get_model(item) # what model?
            parent_obj = parent_model.objects.get(handle=handle) # to add
            ref_handle = pickform.data["picklist"]
            ref_obj = Media.objects.get(handle=ref_handle) 
            dji.add_media_ref_default(parent_obj, ref_obj)
            dji.rebuild_cache(parent_obj) # rebuild cache
            return redirect("/%s/%s%s#tab-media" % (item, handle, build_search(request)))
        else:
            context["pickform"] = pickform
            context["object_handle"] = handle
            context["object_type"] = item
            return render_to_response("pick.html", context)
    elif action == "full":
        media = Media.objects.get(handle=handle)
        media_type, media_ext = media.mime.split("/", 1)
        # FIXME: This should be absolute:
        folder = Config.objects.get(setting="behavior.addmedia-image-dir").value
        # FIXME: media.path should not have any .. for security
        response = HttpResponse(mimetype=media.mime)
        if NEW_PIL or media_ext != "png":
            image = Image.open("%s/%s" % (folder, media.path))
            image.save(response, media_ext)
        else:
            # FIXME: older PIL 1.1.6 cannot read interlaced PNG files
            reader = png.Reader(filename="%s/%s" % (folder, media.path))
            x, y, pixels, meta = reader.asDirect()
            image = png.Image(pixels, meta)
            image.save(response)
        return response
    elif action == "thumbnail":
        media = Media.objects.get(handle=handle)
        media_type, media_ext = media.mime.split("/", 1)
        # FIXME: This should be absolute:
        folder = Config.objects.get(setting="behavior.addmedia-image-dir").value
        # FIXME: media.path should not have any .. for security
        response = HttpResponse(mimetype=media.mime)
        if os.path.exists("%s/thumbnail/%s" % (folder, media.path)):
            if NEW_PIL or media_ext != "png":
                image = Image.open("%s/thumbnail/%s" % (folder, media.path))
                image.save(response, media_ext)
            else:
                # FIXME: older PIL 1.1.6 cannot read interlaced PNG files
                reader = png.Reader(filename="%s/thumbnail/%s" % (folder, media.path))
                x, y, pixels, meta = reader.asDirect()
                image = png.Image(pixels, meta)
                image.save(response)
        else:
            try:
                os.makedirs("%s/thumbnail" % folder)
            except:
                pass
            if NEW_PIL or media_ext != "png":
                image = Image.open("%s/%s" % (folder, media.path))
                image.thumbnail((300,300), Image.ANTIALIAS)
                image.save("%s/thumbnail/%s" % (folder, media.path), media_ext)
                image.save(response, media_ext)
            else:
                # FIXME: older PIL 1.1.6 cannot read interlaced PNG files
                reader = png.Reader(filename="%s/%s" % (folder, media.path))
                x, y, pixels, meta = reader.asDirect()
                meta["interlace"] = False
                image = png.Image(pixels, meta)
                image.save("/tmp/%s" % media.path)
                # Now open in PIL to rescale
                image = Image.open("/tmp/%s" % media.path)
                image.thumbnail((300,300), Image.ANTIALIAS)
                image.save("%s/thumbnail/%s" % (folder, media.path), media_ext)
                image.save(response, media_ext.upper())
        return response
    elif action == "add":
        media = Media(gramps_id=dji.get_next_id(Media, "M"))
        mediaform = MediaForm(instance=media)
        mediaform.model = media
    elif action in ["view", "edit"]: 
        media = Media.objects.get(handle=handle)
        mediaform = MediaForm(instance=media)
        mediaform.model = media
    elif action == "save": 
        media = Media.objects.get(handle=handle)
        mediaform = MediaForm(request.POST, instance=media)
        mediaform.model = media
        if mediaform.is_valid():
            update_last_changed(media, request.user.username)
            media = mediaform.save()
            dji.rebuild_cache(media)
            action = "view"
        else:
            action = "edit"
    elif action == "create": 
        media = Media(handle=create_id())
        mediaform = MediaForm(request.POST, instance=media)
        mediaform.model = media
        if mediaform.is_valid():
            update_last_changed(media, request.user.username)
            media = mediaform.save()
            if add_to:
                item, handle = add_to
                model = dji.get_model(item)
                obj = model.objects.get(handle=handle)
                dji.add_media_ref_default(obj, media)
                dji.rebuild_cache(obj)
                return redirect("/%s/%s#tab-gallery" % (item, handle))
            else:
                dji.rebuild_cache(media)
            action = "view"
        else:
            action = "add"
    elif action == "delete": 
        media = Media.objects.get(handle=handle)
        media.delete()
        return redirect("/media/")
    else:
        raise Exception("Unhandled action: '%s'" % action)

    context["mediaform"] = mediaform
    context["object"] = media
    context["media"] = media
    context["action"] = action
    
    return render_to_response(view_template, context)
