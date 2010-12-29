#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Directory as album.
"""


from glob import glob
import calendar
import config
import gdata.photos #@UnresolvedImport
import log
import os
import photo
import re
import time


class Album:

    album_file = None
    album_id = None
    info_file = None
    
    remote_album = None
    published = None

    def __init__(self, album_file, album_id=None):
        self.album_file = album_file
        
        parsed_album_name = self.parse_album_name()
        self.published = parsed_album_name['published']
        
        if not album_id:
            self.album_id = parsed_album_name['title']
        else:
            self.album_id = album_id
            
        self.info_file = self.album_file + '/' + config.Config().get('settings', 'info_file')

    def get_remote(self):
        if (self.remote_album):
            return self.remote_album 
        
        picasa = config.Config().get('settings', 'picasa_client')
        
        albums = picasa.GetUserFeed(user=config.Config().get('settings', 'user'))
        album = None
        for a in albums.entry:
            if a and (self.__to_unicode(a.gphoto_id.text) == self.__to_unicode(self.album_id) or self.__to_unicode(a.title.text) == self.__to_unicode(self.album_id)):
                album = a
                break
        
        if not album:
            raise Exception('Album does not exist.')
        
        self.remote_album = album
        return album
    
    def __get_published_as_timestamp(self):
        return calendar.timegm(time.strptime(self.published, '%Y-%m-%d'))
    
    def create_remote(self):
        try:
            self.get_remote()
            log.log('warning', 'Album already exists.')
        except Exception as e: #@UnusedVariable
            picasa = config.Config().get('settings', 'picasa_client')
            
            info = self.parse_info_file()
            title = info['title'] or self.album_id
            
            log.log('info', 'Creating remotely new album...')
            self.remote_album = picasa.InsertAlbum(title=title, summary=info['summary'])
            self.sync_info_file(True)
            
            log.log('ok', 'New album created remotely.')
    
    def get_photo(self, photo_file, remote_photo=None):
        return photo.Photo(self.album_file + '/' + photo_file, remote_photo)
    
    def create_remote_photo(self, file):
        p = self.get_photo(os.path.basename(file))
        p.create_remote(self.get_remote().gphoto_id.text)
        return p
    
    def get_remote_photos(self):
        picasa = config.Config().get('settings', 'picasa_client')
        album = self.get_remote()
        photos = picasa.GetFeed('/data/feed/api/user/default/albumid/%s?kind=photo' % album.gphoto_id.text)
        return photos.entry
        
    def get_photos(self):
        return glob(os.path.join(self.album_file, '*.[jJ][pP][gG]'))

    def info_file_exists(self):
        return os.path.exists(self.info_file)
    
    def create_info_file(self):
        log.log('info', 'Creating new info file.')
        remote_album = self.get_remote()
        contents = "%s\n(%s)\n\n%s\n" % (remote_album.title.text, remote_album.location.text, remote_album.summary.text)
        
        info_file = open(self.info_file, 'w')
        info_file.write(contents)
        info_file.close()
        log.log('info', 'New info file created.')
        
    def parse_info_file(self):
        log.log('info', 'Parsing info file.')
        contents = file(self.info_file).read()
        matches = re.compile(r'([^\n]+)\n(\((.+)\)\n)?(\n([^\n]+))?\s*', re.MULTILINE|re.DOTALL).match(contents)
        return { 'title': matches.group(1), 'location': matches.group(3), 'summary': matches.group(5) }
        
    def parse_album_name(self):
        log.log('info', 'Parsing album name.')
        name = os.path.basename(self.album_file)
        matches = re.compile(r'([\d\-]+)\s*(.+)').match(name)
        return { 'title': matches.group(2).strip(), 'published': matches.group(1).strip() }
    
    def sync_info_file(self, force_publishing_date_update=False):
        contents = self.parse_info_file()
        remote_album = self.get_remote()
        
        log.log('info', 'Synchronizing info file values.')
        remote_changed = False
        local_changed = False
        # if local value does not exist in remote album, update this attribute in remote album (and vv)
        for key in contents.iterkeys():
            if (not remote_album.__dict__[key].text) and contents[key]:
                log.log('info', 'Value "%s" updated remotely.' % key)
                remote_album.__dict__[key].text = contents[key]
                remote_changed = True
            elif (not contents[key]) and remote_album.__dict__[key].text:
                log.log('info', 'Value "%s" updated locally.' % key)
                contents[key] = remote_album.__dict__[key].text
                local_changed = True
            else:
                log.log('info', 'Value "%s" left without changes.' % key)
        
        # sync date
        if self.published and (not remote_album.published.text or force_publishing_date_update):
            log.log('info', 'Synchronizing date of publishing.')
            remote_album.published.text = self.published
            remote_changed = True
            # TODO fuck, this doesnt work at all
        
        if remote_changed:
            log.log('info', 'Saving info remotely.')
            picasa = config.Config().get('settings', 'picasa_client')
            self.remote_album = picasa.Put(remote_album, remote_album.GetEditLink().href, converter=gdata.photos.AlbumEntryFromString)

        if local_changed:
            self.create_info_file()

    def __to_unicode(self, object, encoding='utf-8'):
        """Recodes string to Unicode"""
        
        if isinstance(object, basestring):
            if not isinstance(object, unicode):
                object = unicode(object, encoding)
        return object

if __name__ == '__main__':
    pass
    
