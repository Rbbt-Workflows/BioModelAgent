require 'scout'
require 'scout/workflow/python'

Misc.add_libdir if __FILE__ == $PROGRAM_NAME

#require 'rbbt/sources/BioModelAgent'

module BioModelAgent
  extend Workflow
  extend PythonWorkflow


end

#require 'BioModelAgent/tasks/basic.rb'

#require 'rbbt/knowledge_base/BioModelAgent'
#require 'rbbt/entity/BioModelAgent'

