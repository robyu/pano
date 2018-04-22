
import datastore
import time

"""

  
"""
class Webpage:
    dest_dir = 'html'
    templ_header = unicode("""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>Bootstrap 4, from LayoutIt!</title>

    <meta name="description" content="Source code generated using layoutit.com">
    <meta name="author" content="LayoutIt!">

    <link href="css/bootstrap.min.css" rel="stylesheet">
    <link href="css/style.css" rel="stylesheet">

  </head>""")

    templ_container = unicode("""
    <div class="container-fluid">
        {row}
    </div>
    """)

    templ_row = unicode("""
	<div class="row">
	    <div class="col-md-6">
		<h2>
		    Heading
		</h2>
		<p>
		    Donec id elit non mi porta gravida at eget metus. Fusce dapibus, tellus ac cursus commodo, tortor mauris condimentum nibh, ut fermentum massa justo sit amet risus. Etiam porta sem malesuada magna mollis euismod. Donec sed odio dui.
		</p>
		<p>
		    <a class="btn" href="#">View details</a>
		</p><img alt="Bootstrap Image Preview" src="http://www.layoutit.com/img/sports-q-c-140-140-3.jpg">
	    </div>
	    <div class="col-md-6">
		<h2>
		    Heading
		</h2>
		<p>
		    Donec id elit non mi porta gravida at eget metus. Fusce dapibus, tellus ac cursus commodo, tortor mauris condimentum nibh, ut fermentum massa justo sit amet risus. Etiam porta sem malesuada magna mollis euismod. Donec sed odio dui.
		</p>
		<p>
		    <a class="btn" href="#">View details</a>
		</p>
	    </div>
	</div>
    """)
    
    templ_footer=unicode("""
    <script src="js/jquery.min.js"></script>
    <script src="js/bootstrap.min.js"></script>
    <script src="js/scripts.js"></script>
  </body>
</html>
    """)
    
    def __init__(self, dest_fname):
        self.dest_fname = dest_fname
        self.dest_file = open(dest_fname, "wt")
        

        
        
    def OLDgen_webpage(self,dest_fname,cam_name, start_time='now', delta_min = 10, max_age_days=1):
        start_sec = self.db.strtime2sec(start_time)
        assert start_sec > 0

        max_age_sec = start_sec - int(24 * 60 * 60 * max_age_days)
        assert max_age_sec > 0

        delta_sec = int(delta_min * 60)
        assert delta_sec > 0
        
        upper_time_sec = start_sec
        lower_time_sec = upper_time_sec  - delta_sec
        while lower_time_sec > max_age_sec:
            print("| %15d .. %15d |" % (upper_time_sec, lower_time_sec))
            row_image_list = self.db.select_by_time_cam_media(cam_name, upper_time_sec, lower_time_sec,datastore.MEDIA_IMAGE)
            for row in row_image_list:
                print("%d %s %s %s" % (row.d['id'], row.d['cam_name'], row.d['ctime'],row.d['derived_fname']))
            row_video_list = self.db.select_by_time_cam_media(cam_name, upper_time_sec, lower_time_sec,datastore.MEDIA_VIDEO)
            for row in row_video_list:
                print("%d %s %s %s" % (row.d['id'], row.d['cam_name'], row.d['ctime'],row.d['derived_fname']))
            #end

            upper_time_sec = lower_time_sec
            lower_time_sec = upper_time_sec - delta_sec
        #end

        return 

    def gen_webpage(self, cam_name):
        self.dest_file.write(Webpage.templ_header)
        html = Webpage.templ_container.format(row=Webpage.templ_row)
        self.dest_file.write(html)
        self.dest_file.write(Webpage.templ_footer)
        self.dest_file.close()
        
        
        
        
        
        
        
