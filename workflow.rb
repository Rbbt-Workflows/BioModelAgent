require 'scout'
require 'scout/workflow/python'

Misc.add_libdir if __FILE__ == $PROGRAM_NAME

module BioModelAgent
  extend Workflow
end

BioModelAgent.extend PythonWorkflow
