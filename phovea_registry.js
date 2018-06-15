/* *****************************************************************************
 * Caleydo - Visualization for Molecular Biology - http://caleydo.org
 * Copyright (c) The Caleydo Team. All rights reserved.
 * Licensed under the new BSD license, available at http://caleydo.org/license
 **************************************************************************** */

import {register} from 'phovea_core/src/plugin';

/**
 * build a registry by registering all phovea modules
 */
//other modules
import 'phovea_core/phovea_registry.js';
import 'phovea_d3/phovea_registry.js';
import 'phovea_vis/phovea_registry.js';
import 'phovea_ui/phovea_registry.js';
import 'phovea_importer/phovea_registry.js';
import 'phovea_vis_lineup/phovea_registry.js';
import 'phovea_security_flask/phovea_registry.js';
import 'phovea_clue/phovea_registry.js';
import 'phovea_processing_queue/phovea_registry.js';
import 'tdp_core/phovea_registry.js';
import 'pathfinder_ccle/phovea_registry.js';
import 'pathfinder_graph/phovea_registry.js';
//self
register('test',require('./phovea.js'));
