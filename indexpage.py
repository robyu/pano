
import datastore
import time
import os
import dtutils
"""

  
"""
class IndexPage:
# <!-- 
#      placeholders:
#      {camera_overview_rows}
#      {camera_status_cards}
# -->
    templ_webpage = unicode("""
<!DOCTYPE html>
<html lang="en">
    <head>
        <!-- Required meta tags -->
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <meta charset="utf-8">
        <META HTTP-EQUIV="refresh" CONTENT="300"> 

        <title>Panopticon</title>

        <meta name="description" content="panopticon">
        <meta name="author" content="Robert Yu, Buttersquid Inc">
        
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous"> 
	<link rel="stylesheet" href="css/styles.css">

    </head>
    <body >

        <div class="container">  <!- container: allow margins -->
	    <div class="row">
		<h2>
		    Panopticon
		</h2>
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

            {camera_status_cards}
            
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
    templ_overview_row = unicode("""
                    <tr class="table-active" >
                        <td>
                            {camera_name}
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
            # -->
    templ_camera_card = unicode("""
            <div class="card">
                <div class="card-title m-0" id="heading-{camera_name}">
                    <button class="btn btn-link p-0 m-0" data-toggle="collapse" data-target="#collapse-{camera_name}" aria-expanded="true" aria-controls="collapse-{camera_name}">
                        <h3>
                            {camera_name}
                        </h3>
                    </button>
                </div>  <!-- END of collapsible group header -->

                <!-- START of collapsible data -->
                <div id="collapse-{camera_name}" class="collapse show" aria-labelledby="heading-{camera_name}" data-parent="#accordion">
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
                                #      {lower_datetime} - start date
                                #      {upper_datetime} - stop date
                                #      {webpage_url} - URL to media page
                                # -->
    templ_camera_table_row = unicode("""
                                <tr class="table-active" >
                                    <td>
                                        {index}
                                    </td>
                                    <td>
                                        {lower_datetime}
                                    </td>
                                    <td>
                                        {upper_datetime}
                                    </td>
                                    <td>
                                        <a href="{webpage_url}">{webpage_url}</a>
                                    </td>
                                </tr> <!-- END of row -->
                                <!-- TEMPLATE STOP camera-table-row -->
    """)
    

    def __init__(self, www_dir, dest_fname="index.html"):
        self.www_dir = www_dir
        assert os.path.exists(self.www_dir)

        self.dest_fname = dest_fname

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

    def generate_status_rows(self, cam_list):
        """
        generate HTML for status table rows
        """
        cards_html = ''
        for cam_info in cam_list:
            index=0
            rows_html = ''
            for page_dict in cam_info['status_page_list']:
                page_fname = page_dict['page_fname']
                
                # STOPPED HERE
                # sec to iso8601?
                #lower_dt = str(page_dict['lower_time_sec']) #"Sun Aug 26 2018 14:00"
                lower_fmt = "%a %b %d %H:%M:%S"
                upper_fmt = "%H:%M:%S"   # dont render date, only want time
                lower_dt = dtutils.sec_to_str(page_dict['lower_time_sec'],lower_fmt)
                upper_dt = dtutils.sec_to_str(page_dict['upper_time_sec'],upper_fmt)
                rows_html += IndexPage.templ_camera_table_row.format(index=index,
                                                               lower_datetime = lower_dt,
                                                               upper_datetime = upper_dt,
                                                               webpage_url=page_fname)
                index += 1
            #end
            cards_html += IndexPage.templ_camera_card.format(camera_name=cam_info['name'],
                                                     all_table_rows = rows_html)
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
        f.write(IndexPage.templ_webpage.format(camera_overview_rows = overview_html,
                                               camera_status_cards = status_html))
        f.close()

        return self.dest_fname
    
        
        
        
        
