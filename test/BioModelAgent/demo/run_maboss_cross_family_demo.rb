# Work Order B — Step 6 chained demonstration runner.
# Runs the full >=6-hop chain through Scout job().run(true) (NOT direct
# function calls) and records task, inputs, returned path, size, sha256 per hop.
require File.expand_path('../workflow', __dir__)
require 'digest'
require 'json'

WF = BioModelAgent
HOPS = []

def hop(name, inputs)
  job = WF.job(name, inputs)
  job.run(true)
  path = job.load.to_s
  HOPS << { name: name, inputs: inputs.map { |k, v| "#{k}=#{v}" }.join(' ') }
  HOPS.last[:path] = path
  size = File.directory?(path) ? Dir.glob(File.join(path, '*')).map { |f| File.size(f) }.sum : File.size(path)
  HOPS.last[:bytes] = size
  HOPS.last[:sha] = if File.directory?(path)
                      files = Dir.glob(File.join(path, '*')).sort
                      Digest::SHA256.hexdigest(files.map { |f| [File.basename(f), Digest::SHA256.file(f).hexdigest] }.to_json)
                    else
                      Digest::SHA256.file(path).hexdigest
                    end
  lines = File.file?(path) ? `wc -l < #{path}`.strip : nil
  HOPS.last[:lines] = lines
  puts format('  %-32s -> %s', name, path.sub('/home/mvazque2/.scout/var/jobs/', ''))
  path
end

puts 'Hop 1: neko_create_sif'
sif = hop(:neko_create_sif, :genes => 'TP53,MDM2,MYC,AKT1', :max_len => 2,
          :only_signed => 'false', :consensus => 'false')

puts 'Hop 2: neko_remove_bimodal_interactions (bridge requires unimodal)'
sif = hop(:neko_remove_bimodal_interactions, :sif_path => sif)

puts 'Hop 3: neko_remove_undefined_interactions (bnet needs defined signs)'
sif = hop(:neko_remove_undefined_interactions, :sif_path => sif)

puts 'Hop 4: neko_export_bnet (SIF -> .bnet)'
bnet = hop(:neko_export_bnet, :sif_path => sif)

puts 'Hop 5: maboss_bnet_to_bnd_cfg (.bnet -> bundle)'
bundle = hop(:maboss_bnet_to_bnd_cfg, :bnet_path => bnet)

puts 'Hop 6: maboss_set_output_nodes (small output set)'
bundle = hop(:maboss_set_output_nodes, :bundle => bundle, :nodes => 'TP53,MYC')

puts 'Hop 7: maboss_set_initial_state (converted CFG starts empty)'
bundle = hop(:maboss_set_initial_state, :bundle => bundle,
             :nodes => 'TP53,MDM2,MYC,AKT1', :probabilities => '[0.5, 0.5]')

puts 'Hop 8: maboss_update_parameters (explicit small time grid)'
bundle = hop(:maboss_update_parameters, :bundle => bundle,
             :parameters => 'max_time=10,time_tick=1')

puts 'Hop 9: maboss_run_simulation'
tsv = hop(:maboss_run_simulation, :bundle => bundle)

puts 'Hop 10: maboss_plot_trajectories'
png = hop(:maboss_plot_trajectories, :bundle => bundle, :until => 10)

puts 'Hop 11: maboss_simulate_mutation (TP53 knockout)'
mut = hop(:maboss_simulate_mutation, :bundle => bundle, :nodes => 'TP53', :state => 'OFF')

puts
require 'pp'
HOPS.each_with_index do |h, i|
  warn format('hop %-2d %-34s lines=%-6s bytes=%-8d sha=%s',
              i + 1, h[:name], h[:lines] || '-', h[:bytes] || 0, h[:sha][0, 12])
end
pp HOPS.map { |h| h.reject { |k, _| %i[bytes lines].include?(k) } }
