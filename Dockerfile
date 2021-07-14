# Use our Tethyscore base docker image as a parent image
FROM docker.aquaveo.com/tethys/tethysext-atcore/atcore:0.3.0-r16


#####################
# Default Variables #
#####################

ENV TETHYSAPP_DIR /var/www/tethys/apps
ENV APP_DB_HOST ${TETHYS_DB_HOST}
ENV APP_DB_PASSWORD ${TETHYS_DB_PASSWORD}
ENV APP_DB_PORT ${TETHYS_DB_PORT}
ENV APP_DB_USERNAME ${TETHYS_DB_USERNAME}


#########
# SETUP #
#########
RUN mkdir -p "${TETHYSAPP_DIR}"


###########
# INSTALL #
###########
RUN /bin/bash -c ". ${CONDA_HOME}/bin/activate tethys \
  ; pip install django sqlalchemy==1.0.19 flopy"

ADD modflow_adapter ${TETHYSAPP_DIR}/modflow_adapter
ADD tests ${TETHYSAPP_DIR}/modflow_adapter/tests
ADD *.ini ${TETHYSAPP_DIR}/modflow_adapter/
ADD *.py ${TETHYSAPP_DIR}/modflow_adapter/
ADD *.sh ${TETHYSAPP_DIR}/modflow_adapter/
RUN /bin/bash -c ". ${CONDA_HOME}/bin/activate tethys \
  ; cd ${TETHYSAPP_DIR}/modflow_adapter \
  ; conda install -y numpy fiona geopandas pyshp==1.2.12 rasterio\
  ; python setup.py install"

#########
# CHOWN #
#########
RUN export NGINX_USER=$(grep 'user .*;' /etc/nginx/nginx.conf | awk '{print $2}' | awk -F';' '{print $1}') \
  ; find ${TETHYSAPP_DIR} ! -user ${NGINX_USER} -print0 | xargs -0 -I{} chown ${NGINX_USER}: {} \
  ; find /usr/lib/tethys/workspaces ! -user ${NGINX_USER} -print0 | xargs -0 -I{} chown ${NGINX_USER}: {} \
  ; find /usr/lib/tethys/static ! -user ${NGINX_USER} -print0 | xargs -0 -I{} chown ${NGINX_USER}: {} \
  ; find /usr/lib/tethys/keys ! -user ${NGINX_USER} -print0 | xargs -0 -I{} chown ${NGINX_USER}: {} \
  ; find /usr/lib/tethys/src ! -user ${NGINX_USER} -print0 | xargs -0 -I{} chown ${NGINX_USER}: {}


#########################
# CONFIGURE ENVIRONMENT #
#########################
EXPOSE 80


################
# COPY IN SALT #
################
ADD docker/salt/ /srv/salt/


#######
# RUN #
#######
CMD bash run.sh
