window.CAREER_BUDDY_INDUSTRIES = [];

(function() {
    var isDataLoaded = false;

    // Fetch JSON datasets instead of hardcoding
    Promise.all([
        fetch('/static/data/it_departments.json').then(function(r) { return r.json(); }).catch(function() { return []; }),
        fetch('/static/data/nonit_departments.json').then(function(r) { return r.json(); }).catch(function() { return []; })
    ]).then(function(results) {
        var itData = results[0];
        var nonItData = results[1];
        
        var dn = { it: 0, tech: 0, nt: 0 }; 
        
        if (itData && itData.length > 0) {
            itData.forEach(function(mainGroup) {
                if (mainGroup[1] && mainGroup[1].length > 0) {
                    mainGroup[1].forEach(function(dept) {
                        var k = dn['it']++;
                        var key = 'it-' + (k + 1);
                        window.CAREER_BUDDY_INDUSTRIES.push({
                            category: 'it',
                            icon: dept[1],
                            name: dept[0],
                            key: key,
                            roles: (dept[2] || []).map(function(r, j) {
                                return { name: r[0], skills: Array.isArray(r[1]) ? r[1] : [r[1]], key: key + '-' + (j + 1) };
                            })
                        });
                    });
                }
            });
        }
        
        if (nonItData && nonItData.length > 0) {
            nonItData.forEach(function(mainGroup) {
                var groupName = mainGroup[0] || "";
                var cType = (groupName.indexOf("Non-Technical") !== -1 || groupName.indexOf("Business") !== -1) ? 'nt' : 'tech';
                
                if (mainGroup[1] && mainGroup[1].length > 0) {
                    mainGroup[1].forEach(function(dept) {
                        var k = dn[cType]++;
                        var key = cType + '-' + (k + 1);
                        window.CAREER_BUDDY_INDUSTRIES.push({
                            category: cType,
                            icon: dept[1],
                            name: dept[0],
                            key: key,
                            roles: (dept[2] || []).map(function(r, j) {
                                return { name: r[0], skills: Array.isArray(r[1]) ? r[1] : [r[1]], key: key + '-' + (j + 1) };
                            })
                        });
                    });
                }
            });
        }
        
        isDataLoaded = true;
    });

    window.CareerBuddyIndustriesKnowledge = {
        isLoaded: function() {
            return isDataLoaded;
        },
        getAllDepartments: function() {
            return window.CAREER_BUDDY_INDUSTRIES;
        },
        getTechnicalDepartments: function() {
            return window.CAREER_BUDDY_INDUSTRIES.filter(function(d) { return d.category === 'tech'; });
        },
        getNonTechnicalDepartments: function() {
            return window.CAREER_BUDDY_INDUSTRIES.filter(function(d) { return d.category === 'nt'; });
        },
        getITDepartments: function() {
            return window.CAREER_BUDDY_INDUSTRIES.filter(function(d) { return d.category === 'it'; });
        },
        getAllRoles: function() {
            var roles = [];
            window.CAREER_BUDDY_INDUSTRIES.forEach(function(d) {
                d.roles.forEach(function(r) { roles.push({name: r.name, skills: r.skills, department: d.name, category: d.category, key: r.key, deptKey: d.key}); });
            });
            return roles;
        },
        findDepartment: function(query) {
            query = query.toLowerCase();
            return window.CAREER_BUDDY_INDUSTRIES.find(function(d) { return d.name.toLowerCase().indexOf(query) !== -1; });
        },
        findRole: function(query) {
            query = query.toLowerCase();
            return this.getAllRoles().find(function(r) { return r.name.toLowerCase().indexOf(query) !== -1; });
        },
        searchRoles: function(query) {
            query = query.toLowerCase();
            return this.getAllRoles().filter(function(r) {
                return r.name.toLowerCase().indexOf(query) !== -1 || 
                       r.department.toLowerCase().indexOf(query) !== -1 || 
                       r.skills.some(function(s) { return s.toLowerCase().indexOf(query) !== -1; });
            });
        },
        getRouteForCategory: function(c) {
            if (c === 'it') return '/careers/it/';
            if (c === 'tech' || c === 'nt') return '/careers/non-it/';
            return '/careers/non-it/';
        },
        answerIndustriesQuestion: function(query) {
            if (!this.isLoaded()) {
                return { reply: "I am still loading the industries catalog. Please try asking again in a few seconds!", navigation: [] };
            }

            var q = query.toLowerCase().replace(/[?]/g, '');
            var allRoles = this.getAllRoles();
            var allDepts = this.getAllDepartments();
            var itDepts = this.getITDepartments();
            var techDepts = this.getTechnicalDepartments();
            var ntDepts = this.getNonTechnicalDepartments();
            var itRoles = allRoles.filter(function(r) { return r.category === 'it'; });
            var techRoles = allRoles.filter(function(r) { return r.category === 'tech'; });
            var ntRoles = allRoles.filter(function(r) { return r.category === 'nt'; });
            
            // 1. Comparison
            if (q.indexOf("compare") !== -1 || q.indexOf("difference between") !== -1) {
                return {
                    reply: "IT & Engineering focuses on software, data, and digital infrastructure (" + itRoles.length + " roles). Non-IT Technical includes engineering, renewables, and plant operations (" + techRoles.length + " roles). Non-IT Non-Technical covers workforce outsourcing, HRMS, and support services (" + ntRoles.length + " roles).",
                    navigation: [
                        { label: "Explore Industries", route: "/#choose-path" }
                    ]
                };
            }
            if (q.indexOf("most roles") !== -1 || q.indexOf("more roles") !== -1) {
                var counts = [
                    { name: "IT", count: itRoles.length, cat: 'it' },
                    { name: "Non-IT Technical", count: techRoles.length, cat: 'tech' },
                    { name: "Non-IT Non-Technical", count: ntRoles.length, cat: 'nt' }
                ];
                counts.sort(function(a,b) { return b.count - a.count; });
                return {
                    reply: counts[0].name + " currently has the most roles with " + counts[0].count + " roles.",
                    navigation: [{ label: "Open " + counts[0].name, route: this.getRouteForCategory(counts[0].cat) }]
                };
            }
            
            // 2. Counts
            var isCount = q.indexOf("how many") !== -1 || q.indexOf("count") !== -1 || q.indexOf("number of") !== -1;
            if (isCount) {
                var isDeptCount = q.indexOf("department") !== -1 || q.indexOf("categories") !== -1 || q.indexOf("industries") !== -1 && q.indexOf("role") === -1 && q.indexOf("job") === -1;
                
                // Specific department count (e.g. How many roles are in Workforce Outsourcing?)
                var deptMatchCount = allDepts.find(function(d) { return q.indexOf(d.name.toLowerCase().replace(/ & /g, " ")) !== -1 || q.indexOf(d.name.toLowerCase().split(' & ')[0]) !== -1; });
                if (deptMatchCount && (q.indexOf("role") !== -1 || q.indexOf("job") !== -1)) {
                    return {
                        reply: deptMatchCount.name + " has " + deptMatchCount.roles.length + " roles.",
                        navigation: [{ label: "Open " + deptMatchCount.name, route: this.getRouteForCategory(deptMatchCount.category) + '#' + deptMatchCount.key }]
                    };
                }
                
                if (q.indexOf("it") !== -1 && q.indexOf("non") === -1 && q.indexOf("technical") === -1) {
                    if (isDeptCount) return { reply: "There are " + itDepts.length + " IT departments.", navigation: [{ label: "Open IT Roles", route: "/careers/it/" }] };
                    return { reply: "Currently, there are " + itRoles.length + " IT roles.", navigation: [{ label: "Open IT Roles", route: "/careers/it/" }] };
                }
                
                if (q.indexOf("non technical") !== -1 || q.indexOf("non-technical") !== -1 || q.indexOf("non it non technical") !== -1 || q.indexOf("non-it non-technical") !== -1) {
                    if (isDeptCount) return { reply: "There are " + ntDepts.length + " Non-IT Non-Technical departments.", navigation: [{ label: "Open Non-Technical Departments", route: "/careers/non-it/" }] };
                    return { reply: "Currently, there are " + ntRoles.length + " Non-IT Non-Technical roles across " + ntDepts.length + " departments.", navigation: [{ label: "Open Non-IT Non-Technical Roles", route: "/careers/non-it/" }] };
                }
                
                if ((q.indexOf("technical") !== -1 || q.indexOf("non it technical") !== -1 || q.indexOf("non-it technical") !== -1) && q.indexOf("non") === -1) {
                    if (isDeptCount) return { reply: "There are " + techDepts.length + " Non-IT Technical departments.", navigation: [{ label: "Open Technical Departments", route: "/careers/non-it/" }] };
                    return { reply: "Currently, there are " + techRoles.length + " Non-IT Technical roles across " + techDepts.length + " departments.", navigation: [{ label: "Open Non-IT Technical Roles", route: "/careers/non-it/" }] };
                }
                
                // Catch-all general roles or departments count
                if (isDeptCount) {
                    return {
                        reply: "CareerBuddy currently has " + allDepts.length + " departments across its Industries categories.",
                        navigation: [{ label: "Explore Industries", route: "/#choose-path" }]
                    };
                } else if (q.indexOf("role") !== -1 || q.indexOf("job") !== -1) {
                    return {
                        reply: "CareerBuddy currently has " + allRoles.length + " roles across its Industries categories.\n\n• IT: " + itRoles.length + " roles\n• Non-IT Technical: " + techRoles.length + " roles\n• Non-IT Non-Technical: " + ntRoles.length + " roles",
                        navigation: [{ label: "Explore Industries", route: "/#choose-path" }]
                    };
                }
            }
            
            // 3. Skills
            var isSkill = q.indexOf("skill") !== -1 || q.indexOf("require") !== -1;
            if (isSkill) {
                var exactRoleForSkill = this.findRole(query.replace(/what skills are required for|which roles require|what are the requirements for|skills|required|for|this|role|the|\?/gi, "").trim());
                if (exactRoleForSkill) {
                    return {
                        reply: exactRoleForSkill.name + " requires the following skills:\n" + exactRoleForSkill.skills.join(", "),
                        navigation: [{ label: "View " + exactRoleForSkill.name, route: this.getRouteForCategory(exactRoleForSkill.category) + '#' + exactRoleForSkill.key }]
                    };
                }
                
                // Which roles require X skill?
                var skillQuery = query.replace(/which roles require|what roles require|who needs|do you have|jobs|roles|skills|required|for|the|\?/gi, "").trim();
                var sRolesSkill = this.searchRoles(skillQuery);
                if (sRolesSkill.length > 0) {
                    var skRes = "These roles involve " + skillQuery + ":\n";
                    sRolesSkill.slice(0, 5).forEach(function(r) { skRes += "- " + r.name + "\n"; });
                    return {
                        reply: skRes,
                        navigation: sRolesSkill.slice(0, 5).map(function(r) { return { label: "View " + r.name, route: this.getRouteForCategory(r.category) + '#' + r.key }; }.bind(this))
                    };
                }
            }

            // 4. Availability
            var isAvail = q.indexOf("do you have") !== -1 || q.indexOf("are there") !== -1 || q.indexOf("available") !== -1;
            if (isAvail) {
                // Remove prefixes to isolate the subject
                var subject = q.replace(/do you have |are there |what |which |show me |is there a |are |available/g, "").trim();
                if (subject === "roles" || subject === "jobs" || subject === "departments" || subject === "industries" || subject === "") {
                    return {
                        reply: "We have " + allRoles.length + " roles available across IT, Non-IT Technical, and Non-IT Non-Technical industries.",
                        navigation: [{ label: "Explore Industries", route: "/#choose-path" }]
                    };
                }
                
                // First try direct regex for category requests:
                if (q.indexOf("technical") !== -1 && q.indexOf("non") === -1) {
                    return {
                        reply: "Yes, we offer Non-IT Technical roles such as Engineering, Renewables, and EPC.",
                        navigation: [{ label: "Open Non-IT Technical Roles", route: "/careers/non-it/" }]
                    };
                }
                if (q.indexOf("non technical") !== -1 || q.indexOf("non-technical") !== -1) {
                    return {
                        reply: "Yes, we offer Non-IT Non-Technical roles such as Workforce Outsourcing, RPO, and HRMS.",
                        navigation: [{ label: "Open Non-IT Non-Technical Roles", route: "/careers/non-it/" }]
                    };
                }
                if (q.indexOf("it ") !== -1 || q.indexOf(" software") !== -1) {
                    return {
                        reply: "Yes, we offer various IT roles.",
                        navigation: [{ label: "Open IT Roles", route: "/careers/it/" }]
                    };
                }

                var sRoles = this.searchRoles(subject.replace(/ roles| jobs/g, ""));
                if (sRoles.length > 0) {
                    var aRes = "Yes, we have roles related to your query:\n";
                    sRoles.slice(0, 5).forEach(function(r) { aRes += "- " + r.name + " (in " + r.department + ")\n"; });
                    return {
                        reply: aRes,
                        navigation: sRoles.slice(0, 5).map(function(r) { return { label: "View " + r.name, route: this.getRouteForCategory(r.category) + '#' + r.key }; }.bind(this))
                    };
                }
            }
            
            
            // General query
            if (q.indexOf("what industries") !== -1 || q.indexOf("available industries") !== -1 || q === "industries") {
                return {
                    reply: "We support various industries including IT Roles, Non-IT Technical (like Engineering, Renewables, EPC), and Non-IT Non-Technical (like Workforce Outsourcing, RPO, HRMS).",
                    navigation: [
                        { label: "Open IT Roles", route: "/careers/it/" },
                        { label: "Open Non-IT Technical Roles", route: "/careers/non-it/" },
                        { label: "Open Non-IT Non-Technical Roles", route: "/careers/non-it/" }
                    ]
                };
            }
            
            // Exact department check
            var exactDept = this.findDepartment(query);
            if (exactDept) {
                var catLabel = exactDept.category === 'tech' ? 'Non-IT Technical' : (exactDept.category === 'nt' ? 'Non-IT Non-Technical' : 'IT & Engineering');
                var res = "Department:\n" + exactDept.name + "\n\nCategory:\n" + catLabel + "\n\nAvailable roles:\n";
                exactDept.roles.forEach(function(r, idx) { res += (idx + 1) + ". " + r.name + "\n"; });
                return {
                    reply: res,
                    navigation: [
                        { label: "Open " + exactDept.name, route: this.getRouteForCategory(exactDept.category) + '#' + exactDept.key }
                    ]
                };
            }

            // Exact role check
            var exactRole = this.findRole(query);
            if (exactRole) {
                var rCatLabel = exactRole.category === 'tech' ? 'Non-IT Technical' : (exactRole.category === 'nt' ? 'Non-IT Non-Technical' : 'IT & Engineering');
                var reply = "Role:\n" + exactRole.name + "\n\nDepartment:\n" + exactRole.department + "\n\nCategory:\n" + rCatLabel + "\n\nSkills / prerequisites:\n" + exactRole.skills.join(', ');
                return {
                    reply: reply,
                    navigation: [
                        { label: "View " + exactRole.name, route: this.getRouteForCategory(exactRole.category) + '#' + exactRole.key }
                    ]
                };
            }

            // Keywords
            if (q.indexOf("technical") !== -1 && q.indexOf("non") === -1 && (q.indexOf("department") !== -1 || q.indexOf("job") !== -1 || q.indexOf("role") !== -1)) {
                return {
                    reply: "We offer many Technical departments such as Engineering Recruitment, Plant Operations, Renewable Energy, EPC Project Workforce, and more.",
                    navigation: [
                        { label: "Open Non-IT Technical Roles", route: "/careers/non-it/" }
                    ]
                };
            }

            if (q.indexOf("non technical") !== -1 || q.indexOf("non-technical") !== -1 || q.indexOf("non it") !== -1 || q.indexOf("non-it") !== -1) {
                return {
                    reply: "We offer Non-Technical departments such as Workforce Outsourcing & Managed Staffing, Recruitment Process Outsourcing (RPO), Global Workforce Mobility, and more.",
                    navigation: [
                        { label: "Open Non-IT Non-Technical Roles", route: "/careers/non-it/" }
                    ]
                };
            }

            if (q.indexOf("workforce outsourcing") !== -1 || q.indexOf("managed staffing") !== -1 || q.indexOf("outsourcing jobs") !== -1 || q.indexOf("staffing roles") !== -1) {
                var dept = this.findDepartment("Workforce Outsourcing & Managed Staffing");
                if (dept) {
                    var res2 = "Department:\n" + dept.name + "\n\nCategory:\nNon-Technical\n\nAvailable roles:\n";
                    dept.roles.forEach(function(r, idx) { res2 += (idx + 1) + ". " + r.name + "\n"; });
                    return {
                        reply: res2,
                        navigation: [
                            { label: "Open " + dept.name, route: this.getRouteForCategory(dept.category) + '#' + dept.key }
                        ]
                    };
                }
            }
            
            if (q.indexOf("it ") !== -1 || q.indexOf("software") !== -1 || q.indexOf("developer") !== -1 || q.indexOf("programming") !== -1) {
                var itDepts = this.getITDepartments();
                if (itDepts.length > 0) {
                    return {
                        reply: "We offer a variety of IT roles, from Product and Engineering to Data, Security, and more.",
                        navigation: [
                            { label: "Open IT Roles", route: "/careers/it/" }
                        ]
                    };
                }
            }

            var searchRes = this.searchRoles(query);
            if (searchRes.length > 0) {
                var res3 = "I found some roles related to \"" + query + "\":\n";
                searchRes.slice(0, 5).forEach(function(r) { res3 += "- " + r.name + " (in " + r.department + ")\n"; });
                if (searchRes.length > 5) res3 += "...and " + (searchRes.length - 5) + " more. Which one would you like?";
                else if (searchRes.length > 1) res3 += "\nWhich one would you like?";
                
                var nav = searchRes.slice(0, 5).map(function(r) {
                     return { label: "View " + r.name, route: this.getRouteForCategory(r.category) + '#' + r.key };
                }.bind(this));
                
                return { reply: res3, navigation: nav };
            }
            
            return null;
        }
    };
})();
