import { apiClient } from './client.js';
import { CONFIG } from '../config.js';

export async function getAgentManifest() {
  return await apiClient.request(CONFIG.ENDPOINTS.AGENT_MANIFEST);
}

export async function getAgentSkills() {
  const response = await apiClient.request(CONFIG.ENDPOINTS.AGENT_SKILLS);
  return response?.skills || [];
}

export async function getSkillDetails(skillId) {
  return await apiClient.request(`${CONFIG.ENDPOINTS.AGENT_SKILL_DETAILS}/${skillId}`);
}

export async function resolveDID(did) {
  return await apiClient.request(CONFIG.ENDPOINTS.DID_RESOLVE, {
    method: 'POST',
    body: JSON.stringify({ did })
  });
}

export async function loadFullAgentInfo() {
  try {
    const manifest = await getAgentManifest();
    const skills = await getAgentSkills();
    
    let didDocument = null;
    const didExtension = manifest?.capabilities?.extensions?.find(ext => ext.uri?.startsWith('did:'));
    
    if (didExtension?.uri) {
      try {
        didDocument = await resolveDID(didExtension.uri);
      } catch (error) {
        console.error('Error loading DID document:', error);
      }
    }
    
    return {
      manifest,
      skills,
      didDocument
    };
  } catch (error) {
    console.error('Error loading agent info:', error);
    throw error;
  }
}
