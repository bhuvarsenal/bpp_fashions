from flask import request, jsonify, current_app
from flask.views import MethodView

from flaskapp.database import SessionLocal
from flask_smorest import Blueprint, abort

from flaskapp.service.catalog import CatalogService
from flaskapp.service.file import FileService
from flaskapp.service.ingestion import IngestionService
from flaskapp.schemas import MultiPartFileSchema

from threading import Thread
import uuid

db = SessionLocal()
blp = Blueprint("ingestion", __name__, description="Ingest catalog into system")


@blp.route("/api/upload-catalog/<string:site_key>")
class IngestCatalog(MethodView):
    @blp.arguments(MultiPartFileSchema, location="files")
    @blp.response(201)
    def post(self, files, site_key):
        if not IngestionService.validate_site_key(current_app.config['SITE_KEY'], site_key):
            abort(401, message="Invalid Site Key")
        if request.method == "POST":
            if "file" not in files:
                abort(400, message="No File Selected")

            file = files["file"]

            extension = FileService.get_file_extension(file.filename)
            if extension is None:
                abort(400, message="Invalid File")

            catalog_processor_class = IngestionService.get_catalog_processor(extension)
            if catalog_processor_class is None:
                abort(400, message="File Type Not Supported")

            filepath = FileService.save_file(current_app.config['UPLOAD_FOLDER'], file)
            if filepath is None:
                abort(400, "No File Selected")

            catalog_processor = catalog_processor_class(filepath)
            tracking_id = str(uuid.uuid4().hex)

            CatalogService\
                .create_and_save(tracking_id,
                                 catalog_processor_class.STATUS_CODES.get("VALIDATING", "Unavailable"),
                                 filepath)


            response = {
                "message": "File Uploaded Successfully",
                "tracking ID": tracking_id
            }

            try:
                Thread(target=IngestionService.ingest_catalog, args=("_", tracking_id, catalog_processor)).start()
            except Exception as e:
                print("Exception in ingestion:", e)

            return jsonify(response)