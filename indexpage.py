
import datastore
import time
import os
import dtutils
import logging

"""

  
"""
class IndexPage:
# <!-- 
#      placeholders:
#      {camera_overview_rows}
#      {camera_status_cards}
# -->
    templ_webpage = str("""
<!DOCTYPE html>
<html lang="en">
    <head>
        <!-- Required meta tags -->
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <meta charset="utf-8">
        <META HTTP-EQUIV="refresh" CONTENT="60"> 

        <title>Panopticon</title>

        <meta name="description" content="panopticon">
        <meta name="author" content="Robert Yu, Buttersquid Inc">
        
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous"> 
	<link rel="stylesheet" href="css/styles.css">

    </head>
    <body >

        <div class="container">  <!- container: allow margins -->
            <div class="col-sm">
 	        <div class="row">
		    <h2>
		        Panopticon
		    </h2>
                </div>
	        <div class="row">
		        Updated {update_date_time}
                </div>
            </div>

            <!--  SUMMARY TABLE HEADER -->
	    <table class="table table-sm table-striped table-dark"> <!-- compact table, striped -->
		<thead>
		    <tr>
			<th>
			    Camera Name
			</th>
			<th>
			    Description
			</th>
 			<th>
			    Admin Login
			</th>
 			<th>
			    Live Video
			</th>
		    </tr>
		</thead>
                
                <!-- SUMMARY ROWS -->
                <tbody>
                    {camera_overview_rows}
                </tbody>
	    </table>
            
            <div class="accordion" id="accordionContainer">
            {camera_status_cards}
            </div>
            
	</div>
        
        <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.9/umd/popper.min.js" integrity="sha384-ApNbgh9B+Y1QKtv3Rn7W3mgPxhU9K/ScQsAP7hUibX39j7fakFPskvXusvfa0b4Q" crossorigin="anonymous"></script>
        <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>
        <script src="js/scripts.js"></script>
    </body>
</html>
    """)

                    # <!-- TEMPLATE START camera-overview
                         
                    #      placeholders:
                    #      {camera_name}
                    #      {camera_descr}
                    #      {admin_url}
                    #      {live_url}
                    # -->
    templ_overview_row = str("""
                    <tr class="table-active" >
                        <td>
                            <!-- this href allows us to expand/collapse associated media rows  -->
                            <a href="collapse-{camera_name}" data-toggle="collapse" id="button-{camera_name}"  data-target="#collapse-{camera_name}" aria-expanded="true" aria-controls="collapse-{camera_name}">
                                {camera_name}
                            </a>
                        </td>
                        <td>
                            {camera_descr}
                        </td>
                        <td>
                            <a href="{admin_url}">admin_url</a>
                        </td>
                        <td>
                            <a href="{live_url}">live-link</a>
                        </td>
                    </tr>
                    <!--  TEMPLATE END -->
    """)

            # <!-- TEMPLATE START camera-table-card

            #      placeholders:
            #      {camera_name}
            #      {all_table_rows}
            #      {recent_thumbnail}
            #      {earliest_dt} - earliest date-time string
            #      {latest_dt} - latest date-time string
            # -->
    templ_camera_card = str("""
            <div class="card">
                <div class="card-title m-0" id="heading-{camera_name}">
                    <button class="btn btn-link p-0 m-0" data-toggle="collapse" id="button-{camera_name}" data-target="#collapse-{camera_name}" aria-expanded="true" aria-controls="collapse-{camera_name}">
                        <h3 class="text-left">
                            {camera_name}
                        </h3>
                        <p clas="text-left">
                            {earliest_dt}..{latest_dt}
                        </p>
                    </button>
                    <button class="btn btn-link p-1 m-1 border border-success" data-toggle="collapse" id="button-{camera_name}" data-target="#collapse-{camera_name}" aria-expanded="true" aria-controls="collapse-{camera_name}">
                        <img src="{recent_thumbnail}" alt="latest_image">
                    </button>
                </div>  <!-- END of collapsible group header -->

                <!-- START of collapsible data -->
                <div id="collapse-{camera_name}" class="collapse hide" aria-labelledby="heading-{camera_name}" data-parent="#accordionContainer">
                    <div class="card-body p-0">
	                <table class="table table-sm table-striped table-dark">
		            <thead>
		                <tr>
			            <th>
			                #
			            </th>
                                    <th>
                                        Start 
                                    </th>
                                    <th>
                                        Stop
                                    </th>
			            <th>
			                Status Page
			            </th>
		                </tr>
		            </thead>
                            
                            
                            <!-- CAMERA STATUS ROWS -->
                            <tbody>
                                <!-- INSERT camera-table-rows here -->
                                {all_table_rows}
                            </tbody>
                        </table>
                    </div>
                </div> <!-- END of collapsible data  -->
            </div> <!-- END card -->
            <!-- TEMPLATE END camera-table-card -->
    """)

                                # <!-- TEMPLATE START camera-table-row
                                     
                                #      placeholders:
                                #      {index}
                                #      {earlier_datetime} - start date
                                #      {later_datetime} - stop date
                                #      {webpage_url} - URL to media page
                                # -->
    templ_camera_table_row = str("""
                                <tr class="table-active" >
                                    <td>
                                        <a href="{webpage_url}">{index}</a>
                                    </td>
                                    <td>
                                        <a href="{webpage_url}">{earlier_datetime}</a>
                                    </td>
                                    <td>
                                        <a href="{webpage_url}">{later_datetime}</a>
                                    </td>
                                    <td>
                                        <a href="{webpage_url}">{webpage_url}</a>
                                    </td>
                                </tr> <!-- END of row -->
                                <!-- TEMPLATE STOP camera-table-row -->
    """)
    

    def __init__(self,
                 db,
                 www_dir,
                 derived_dir,
                 www_derived_dir,
                 dest_fname="index.html"):
        self.www_dir = www_dir
        assert os.path.exists(self.www_dir), "www_dir does not exist: %s" % www_dir
        
        self.derived_dir = derived_dir
        self.www_derived_dir = www_derived_dir

        self.dest_fname = dest_fname
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.default_image_fname = 'mryuck.png'

    def generate_overview_rows(self, cam_list):
        """
        generate HTML for summary table rows
        """
        rows_html = ''
        for cam_info in cam_list:
            rows_html += IndexPage.templ_overview_row.format(camera_name = cam_info['name'],
                                                            camera_descr = cam_info['description'],
                                                            admin_url=cam_info['admin_url'],
                                                            live_url = cam_info['live_url'])
        #end
        return rows_html

    def get_latest_thumb_url(self, cam_name):
        """
        given a camera name,
        get the URL (the www path) of the latest thumbnail
        """
        latest_image_entry = self.db.select_latest_image_per_camera(cam_name)
        thumb_path=latest_image_entry[0].d['derived_fname']

        # sometimes, latest_image_entry[0] is a bogus database entry.
        # this occurs when there are no derived thumbnails.
        # so we must check if thumb_path is None.

        if thumb_path==None or  os.path.exists(thumb_path)==False:
            self.logger.info("%s does not exist" % thumb_path)
            thumb_path = self.default_image_fname
        #end
        thumb_path2 = thumb_path.replace(self.derived_dir, self.www_derived_dir)
        return thumb_path2
    
    def generate_status_rows(self, cam_list):
        """
        generate HTML for status table rows
        """
        earlier_fmt = "%a %b %d %H:%M:%S"
        later_fmt = "%a %b %d %H:%M:%S"   
        cards_html = ''
        for cam_info in cam_list:
            if 'status_page_list' in cam_info:
                num_status_pages = len(cam_info['status_page_list'])
            else:
                num_status_pages = 0
                self.logger.debug("'status_page_list' not defined for this camera; CamPage not yet run for (%s)" % cam_info['name'])
            #end
            self.logger.debug("cam (%s) has %d status pages" % (cam_info['name'], num_status_pages))
            if num_status_pages > 0:  # at least one status page
                # note earliest/latest times from first and last entries
                latest_time_sec = cam_info['status_page_list'][0]['later_time_sec']
                earliest_time_sec = cam_info['status_page_list'][num_status_pages-1]['earlier_time_sec']

                rows_html = ''
                for index in range(len(cam_info['status_page_list'])):
                    page_dict = cam_info['status_page_list'][index]
                    page_fname = page_dict['page_fname']
                
                    # sec to iso8601?
                    #earlier_dt = str(page_dict['earlier_time_sec']) #"Sun Aug 26 2018 14:00"
                    earlier_dt = dtutils.sec_to_str(page_dict['earlier_time_sec'],earlier_fmt)
                    later_dt = dtutils.sec_to_str(page_dict['later_time_sec'],later_fmt)
                    rows_html += IndexPage.templ_camera_table_row.format(index=index,
                                                                         earlier_datetime = earlier_dt,
                                                                         later_datetime = later_dt,
                                                                         webpage_url=page_fname)

                #end
                assert earliest_time_sec < latest_time_sec, "earliest_time_sec (%d) < latest_time_sec (%d)" % (earliest_time_sec, latest_time_sec)
                earliest_dt = dtutils.sec_to_str(earliest_time_sec,earlier_fmt)
                latest_dt = dtutils.sec_to_str(latest_time_sec,later_fmt)
                latest_thumbnail_url = self.get_latest_thumb_url(cam_info['name'])
                cards_html += IndexPage.templ_camera_card.format(camera_name=cam_info['name'],
                                                                 all_table_rows = rows_html,
                                                                 earliest_dt = earliest_dt,
                                                                 latest_dt = latest_dt,
                                                                 recent_thumbnail=latest_thumbnail_url)
                
            #end
        #end
        return cards_html
        
    def make_index(self, cam_list):
        """
        IN:
        cam_list:  list of per-cam dictionary objects
        """
        overview_html = self.generate_overview_rows(cam_list)
        status_html = self.generate_status_rows(cam_list)

        full_dest_fname = os.path.join(self.www_dir, self.dest_fname)
        f = open(full_dest_fname, "wt")
        f.write(IndexPage.templ_webpage.format(update_date_time = dtutils.now_to_str(),
                                               camera_overview_rows = overview_html,
                                               camera_status_cards = status_html))
        f.close()

        return self.dest_fname
    
        
        
        
        
