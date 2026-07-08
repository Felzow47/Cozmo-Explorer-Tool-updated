let isRunning = false;
let isMouseDown, isHeadlightEnabled, isFreeplayEnabled, isFocusOnInput = false;
let tempListID = null;
let isPlayingListID = null;
let stopTimeOut;
let socket;
let imageInterval, mousedownInterval, mouseKeyCode, animateHTML;
let cozmoUpdateInterval = null;
let cozmoReconnectPollInterval = null;

let currentTab = 'animations';

const KEYBOARD_LAYOUT_STORAGE_KEY = 'cozmoKeyboardLayout';
const LOGICAL_CONTROL_KEYS = ['W', 'S', 'A', 'D', 'Q', 'E', 'R', 'F'];
const LOGICAL_KEYCODES = {W: 87, S: 83, A: 65, D: 68, Q: 81, E: 69, R: 82, F: 70};
const AZERTY_PHYSICAL_TO_LOGICAL = {90: 87, 81: 65, 83: 83, 68: 68, 65: 81, 69: 69, 82: 82, 70: 70};
const AZERTY_LABELS = {W: 'Z', S: 'S', A: 'Q', D: 'D', Q: 'A', E: 'E', R: 'R', F: 'F'};
let keyboardLayout = 'qwerty';

function loadKeyboardLayout() {
    try {
        let saved = localStorage.getItem(KEYBOARD_LAYOUT_STORAGE_KEY);
        if (saved === 'azerty' || saved === 'qwerty') {
            keyboardLayout = saved;
        }
    } catch (e) {}
}

function saveKeyboardLayout() {
    try {
        localStorage.setItem(KEYBOARD_LAYOUT_STORAGE_KEY, keyboardLayout);
    } catch (e) {}
}

function getLayoutLabel(logicalKey) {
    if (keyboardLayout === 'azerty' && AZERTY_LABELS[logicalKey]) {
        return AZERTY_LABELS[logicalKey];
    }
    return logicalKey;
}

function remapKeyCodeForLayout(keyCode) {
    if (keyboardLayout === 'azerty' && AZERTY_PHYSICAL_TO_LOGICAL[keyCode] !== undefined) {
        return AZERTY_PHYSICAL_TO_LOGICAL[keyCode];
    }
    return keyCode;
}

function logicalKeyFromKeyCode(keyCode) {
    for (let i = 0; i < LOGICAL_CONTROL_KEYS.length; i++) {
        let key = LOGICAL_CONTROL_KEYS[i];
        if (LOGICAL_KEYCODES[key] === keyCode) {
            return key;
        }
    }
    return null;
}

function updateControlButtonLabels() {
    for (let i = 0; i < LOGICAL_CONTROL_KEYS.length; i++) {
        let key = LOGICAL_CONTROL_KEYS[i];
        $('#ctrl_btn_' + key).text(getLayoutLabel(key));
    }
    $('#keyboard-layout-toggle').text(keyboardLayout === 'azerty' ? 'AZERTY' : 'QWERTY');
}

function initKeyboardLayoutToggle() {
    loadKeyboardLayout();
    $('#keyboard-layout-toggle').text(keyboardLayout === 'azerty' ? 'AZERTY' : 'QWERTY');
    $('#keyboard-layout-toggle').click(function () {
        keyboardLayout = keyboardLayout === 'qwerty' ? 'azerty' : 'qwerty';
        saveKeyboardLayout();
        updateControlButtonLabels();
    });
}

window.COZMO_APP = window.COZMO_APP || {
    anims_raw: '',
    triggers_raw: '',
    behaviors_raw: '',
    hasSocketIO: false,
    hasPillow: false,
    hasCamera: false,
    robotConnected: false
};

function applyCozmoFlagsFromPage() {
    var app = window.COZMO_APP;
    if (!window.COZMO_UI) {
        return;
    }
    app.hasSocketIO = !!window.COZMO_UI.hasSocketIO;
    app.hasPillow = !!window.COZMO_UI.hasPillow;
    app.hasCamera = !!window.COZMO_UI.hasCamera;
    app.robotConnected = !!window.COZMO_UI.robotConnected;
}

function applyCozmoLists(data) {
    if (!data) {
        return false;
    }
    var app = window.COZMO_APP;
    app.anims_raw = data.anims_raw || '';
    app.triggers_raw = data.triggers_raw || '';
    app.behaviors_raw = data.behaviors_raw || '';
    if (data.robotConnected !== undefined) {
        app.robotConnected = !!data.robotConnected;
    }
    if (data.hasCamera !== undefined) {
        app.hasCamera = !!data.hasCamera;
    }
    if (!window.COZMO_UI) {
        if (data.hasPillow !== undefined) {
            app.hasPillow = !!data.hasPillow;
        }
        if (data.hasSocketIO !== undefined) {
            app.hasSocketIO = !!data.hasSocketIO;
        }
    }
    return true;
}

function getBootstrapUrl() {
    if (window.COZMO_CONFIG && window.COZMO_CONFIG.bootstrapUrl) {
        return window.COZMO_CONFIG.bootstrapUrl;
    }
    return '/ui-bootstrap';
}

function loadCozmoBootstrap(callback) {
    applyCozmoFlagsFromPage();
    var bootstrapUrl = getBootstrapUrl();
    fetch(bootstrapUrl)
        .then(function (response) {
            if (!response.ok) {
                throw new Error('bootstrap http ' + response.status);
            }
            return response.json();
        })
        .then(function (data) {
            applyCozmoLists(data);
            callback(true);
        })
        .catch(function (bootstrapError) {
            console.log('bootstrap load failed', bootstrapError);
            callback(false);
        });
}

function applyDemoListsIfNeeded() {
    var app = window.COZMO_APP;
    if (!app.robotConnected && app.anims_raw === '') {
        app.anims_raw = 'anim_cozmo_test_01,anim_cozmo_test_02,anim_cozmo_test_03,anim_cozmo_test_04,anim_cozmo_test_05,anim_more_test_01,anim_more_test_02,anim_more_test_03,anim_more_test_04';
        app.triggers_raw = 'TestTriggerClass01,TestTriggerClass02,TestTriggerClass03,TestTriggerClass04,TestTriggerClass05';
        app.behaviors_raw = 'InCaseYouDidNotNotice,ThisIsTestData,CozmoIsNotConnected';
    }
}

function refreshListArrays() {
    var app = window.COZMO_APP;
    animations.list = stringSorting(app.anims_raw);
    triggers.list = stringSorting(app.triggers_raw);
    behaviors.list = stringSorting(app.behaviors_raw);
}

function removeDemoReconnectMessages() {
    $('#event-content li.demo-reconnect-msg').remove();
}

function startCozmoUpdateLoop() {
    if (cozmoUpdateInterval) {
        return;
    }
    cozmoUpdateInterval = setInterval(function () {
        postHttpRequest('updateCozmo', {});
    }, 50);
}

function stopRobotReconnectPoll() {
    if (cozmoReconnectPollInterval) {
        clearInterval(cozmoReconnectPollInterval);
        cozmoReconnectPollInterval = null;
    }
}

function refreshUiAfterRobotConnect() {
    loadCozmoBootstrap(function (bootstrapOk) {
        if (!bootstrapOk) {
            return;
        }
        refreshListArrays();
        var fragMap = {animations: 0, triggers: 1, behaviors: 2};
        var fragId = '#fragment-' + fragMap[currentTab];
        $(fragId).html('');
        initAnimationList($(fragId), currentTab);

        removeDemoReconnectMessages();
        $('#event-content').prepend('<li style="background-color: lightgreen">Cozmo connected.</li>');

        if (window.COZMO_UI) {
            window.COZMO_UI.robotConnected = true;
            window.COZMO_UI.hasCamera = window.COZMO_APP.hasCamera;
        }

        startCozmoUpdateLoop();
        stopRobotReconnectPoll();
    });
}

function startRobotReconnectPoll() {
    if (window.COZMO_APP.robotConnected) {
        return;
    }
    stopRobotReconnectPoll();
    cozmoReconnectPollInterval = setInterval(function () {
        if (window.COZMO_APP.robotConnected) {
            stopRobotReconnectPoll();
            return;
        }
        fetch('/health')
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('health http ' + response.status);
                }
                return response.json();
            })
            .then(function (data) {
                if (data.robotConnected) {
                    refreshUiAfterRobotConnect();
                }
            })
            .catch(function () {});
    }, 5000);
}

stringSorting = function (str) {
    let array = str.split(',');
    array.sort();
    return array
};

let animations = {
    name: 'animations',
    list: [],
    str: '',
    active: 0,
    info: 'A list of animations. Pick an animation from the list and click the play button to animate Cozmo.<br/><br/>For copying to clipboard:<br/>A.) use the copy button, OR<br/>B.) select a line of text and press Ctrl-C'};
let triggers = {
    name: 'triggers',
    list: [],
    str: '',
    active: 0,
    info: 'A list of animation sets. This differs from the Animation list in that each time you press the same animation from the list, it may play out slightly different. This offers letiety: it makes Cozmo seem more alive if you use triggers in your own code.<br/><br/>For copying to clipboard:<br/>A.) use the copy button, OR<br/>B.) select a line of text and press Ctrl-C'};
let behaviors = {
    name: 'behaviors',
    list: [],
    str: '',
    active: 0,
    info: 'A list of behaviors. Behaviors represent a task that Cozmo may perform for an indefinite amount of time. Animation Explorer limits active time to 30 seconds. You can abort by pressing the \'stop\' button.<br/><br/>For copying to clipboard:<br/>A.) use the copy button, OR<br/>B.) select a line of text and press Ctrl-C'};

let listArray = [animations, triggers, behaviors];

let listButtons = '' +
    '<div id="list-buttons">' +
        // '<i id="btn-explanation" class="fa fa-question box"></i>' +
        '<i id="btn-copy-clipboard" class="fa fa-copy box"></i>' +
        '<i id="btn-play-stop" class="fa fa-play box"></i>' +
    '</div>';

// sending and receiving json from server
getHttpRequest = function (url, dataSet)
{
    if(url != 'toggle_pose' && !isRunning) {
        checkRunning(true);
    }
    let xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE) {
            if(isRunning) {
                if (currentTab == 'behaviors'){
                    stopTimeOut = setTimeout(function(){
                            if(isRunning && currentTab == 'behaviors') {
                                console.log('stopTimeOut triggered');
                                getHttpRequest('stop', '');
                                checkRunning(false);
                            }
                        },
                        30000 // run behavior for 30 seconds
                    );
                } else {
                    checkRunning(false);
                }
            }
        }
    };
    xhr.open('POST', url, true);
    xhr.send(JSON.stringify(dataSet));
};

function postHttpRequest(url, dataSet)
{
    let xhr = new XMLHttpRequest();
    xhr.open("POST", url, true);
    xhr.send( JSON.stringify( dataSet ) );
}

// while running (or not) toggle elements
checkRunning = function (bool) {
    isRunning = bool;

    if (bool){
        $('.item-list').addClass('greyed-out');
        $('#list-buttons').parent().addClass('bg-playing');
        $('#c-play').show();
        $('#c-eyes').hide();
        $('#btn-play-stop').addClass('red');
        if(currentTab == 'behaviors') {
            $('#btn-play-stop').addClass('fa-stop');
        } else {
            $('#btn-play-stop').hide();
        }
        $('.bg-just-played').removeClass('bg-just-played');
        isPlayingListID = $('#list-buttons').parent();
    } else {
        if(isPlayingListID != null) {
            isPlayingListID.toggleClass('bg-playing bg-just-played');
            isPlayingListID = null;
        }
        $('.item-list').removeClass('greyed-out');
        $('#c-play').hide();
        $('#c-eyes').show();
        if(currentTab == 'behaviors') {
            $('#btn-play-stop').removeClass('fa-stop');
        } else {
            $('#btn-play-stop').show();
        }
        if($('#list-buttons').length && $('#list-buttons').parent().is(':hover')){
            $('#btn-play-stop').removeClass('red');
        } else {
            $('#list-buttons').remove();
            if(tempListID != null){
                createListButtons(tempListID);
            }
        }
    }
};

// store text value in OS clipboard
function copyTextToClipboard(text) {
    let textArea = document.createElement('textarea');
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();

    try {
        document.execCommand('copy');
    } catch (err) {
        console.log('ERROR: unable to copy text to clipboard');
    }

    document.body.removeChild(textArea);
}

function loadArray(){
    let array = [];
    if (currentTab == 'animations'){
        array = animations;
    } else if (currentTab == 'triggers'){
        array = triggers;
    } else if (currentTab == 'behaviors'){
        array = behaviors;
    }
    return array
}

// hide list item if string from search box does not match list item text
function matchCharacters(str){
    let array = loadArray();

    for(let i = 0; i < array.list.length; i++){
        let elem = $('#li_' + i);
        if (array.list[i].toLowerCase().indexOf(str.toLowerCase()) != -1){
            elem.show();
        } else {
            elem.hide();
        }
    }
    console.log('matching character(s): ' + str);
    showClear(str);
}

// show clear button when search box value is not empty
function showClear(str){
    if(str == ''){
        $('.filterclear').css('visibility', 'hidden');
        $('.filtersubmit').css('visibility', 'visible');
    } else {
        $('.filterclear').css('visibility', 'visible');
        $('.filtersubmit').css('visibility', 'hidden');
    }
}

// create list
function createList(array){
    for (let i =0; i < array.list.length; i++) {
        $('#ul-animations').append('<li id="li_' + i + '" class="item-list"><span>' + array.list[i] + '</span></li>');
        let li = $('#li_' + i);
        li.mouseenter(function () {
            if(!isRunning) {
                if ($('#list-buttons').length) {
                    $('#list-buttons').remove();
                }
                tempListID = $(this);
                createListButtons($(this));
            }
        });
        li.mouseleave(function () {
            tempListID = null;
            if($('#list-buttons').length && !isRunning) {
                $('#list-buttons').remove();
            }
        })
    }
}

// create buttons for list item
function createListButtons(item){
    if(!isRunning && !isMouseDown) {
        item.append(listButtons);
        $('#btn-play-stop').click(function () {
            let array = loadArray();
            if(!isRunning) {
                getHttpRequest('play_' + array.name.substr(0, array.name.length - 1), $('#list-buttons').parent().text()); // start specific animation
            }else {
                getHttpRequest('stop', ''); // abort action
                checkRunning(false);
            }
        });
        $('#btn-copy-clipboard').click(function () {
            let textObj = $('#list-buttons').parent().children(":first");
            let str = textObj.text();
            textObj.text('copied to clipboard');
            //parent.mouseenter(); // this behaves quirky
            copyTextToClipboard(str);
            console.log(str);
            setTimeout(function() {
                textObj.text(str);
                //parent.mouseenter(); // this behaves quirky
            }, 600);
        });
        $('#btn-explanation').click(function () {
/*
            if (!$('#copied').length) {
                let str = $('#list-buttons').parent().text();
                copyTextToClipboard(str);
                $('#list-buttons').parent().append('<div id="copied">copied to clipboard</div>');
                console.event-content(str);
                setTimeout(function () {
                    $('#copied').remove();
                }, 600);
            }
*/
        })
    }
}

function initSearch() {
    // evaluate search input value after every entered key
    $('.search').bind('input', function (){
        let str = $('.search').val();
        matchCharacters(str);
    });

    // clear search box value
    $('.filterclear').click(function (){
        $('.search').val('');
        matchCharacters('');
    });
}

function createGroupButtons() {
    // create group buttons
    let groupButtons = [];

    for (let j=0; j < animations.list.length; j++){
        let str = animations.list[j];
        let n = str.indexOf("_");
        str = str.substr(n+1);
        n = str.indexOf("_");
        str = str.substr(0, n);

        let match = false;
        for(let k = 0; k < groupButtons.length;k++){
            if(groupButtons[k] == str){
                match = true;
                break
            }
        }
        if(!match && animations.list[j].indexOf('anim_') > -1){
            groupButtons[groupButtons.length] = str;
            $('#group-content').append('<button id="btn-' + str + '" class="flex-item ui-button ui-widget ui-corner-all">' + str + '</button>');
            $('#btn-' + str).click(function(){
                if (!isRunning) {
                    let str = $(this).text();
                    if ($('.search').val() == str) {
                        str = '';
                    }
                    $('.search').val(str);
                    matchCharacters(str);
                }
            })
        }
    }
}

function updateImage() {
    if (window.COZMO_APP.hasCamera) {
        document.getElementById("cozmoImageId").src = "/cozmoImage?" + (new Date()).getTime();
    } else if (!window.COZMO_APP.hasPillow) {
        clearInterval(imageInterval);
    }
}

function handleKeyActivity (e, actionType)
{
    if(!isFocusOnInput) {
        let keyCode = (e.keyCode ? e.keyCode : e.which);
        let logicalKeyCode = remapKeyCodeForLayout(keyCode);
        let hasShift = (e.shiftKey ? 1 : 0);
        let hasCtrl = (e.ctrlKey ? 1 : 0);
        let hasAlt = (e.altKey ? 1 : 0);

        let bID = [0, ''];
        let logicalKey = logicalKeyFromKeyCode(logicalKeyCode);
        if (logicalKey) {
            bID = [0, '#ctrl_btn_' + logicalKey];
        }
        if (keyCode == 16) {
            bID = [1, '#ctrl_state_SHIFT']
        } // SHIFT
        if (keyCode == 18) {
            bID = [1, '#ctrl_state_ALT']
        }   // ALT
        if (keyCode == 73) {
            bID = [2, '#ctrl_toggle_I']
        }   // I
        if (keyCode == 80) {
            bID = [2, '#ctrl_toggle_P']
        }   // P

        if (actionType == "keyup") {
            if (bID[0] == 0) {
                $(bID[1]).removeClass('control-button-active');
            } else if (bID[0] == 1) {
                $(bID[1]).removeClass('control-state-active');
            }

        } else {
            if (bID[0] == 0) {
                $(bID[1]).addClass('control-button-active');
            } else if (bID[0] == 1) {
                $(bID[1]).addClass('control-state-active');
            }
        }

        if(hasShift == 0 && hasCtrl == 0 && hasAlt == 0) {
            if (keyCode == 73 && actionType == 'keydown') {
                isHeadlightEnabled = !isHeadlightEnabled;
                if (isHeadlightEnabled) {
                    $(bID[1]).addClass('control-toggle-active');
                } else {
                    $(bID[1]).removeClass('control-toggle-active');
                }
                postHttpRequest("setHeadlightEnabled", {isHeadlightEnabled});
                return
            } else if (keyCode == 80 && actionType == 'keydown') {
                isFreeplayEnabled = !isFreeplayEnabled;
                if (isFreeplayEnabled) {
                    $(bID[1]).addClass('control-toggle-active');
                } else {
                    $(bID[1]).removeClass('control-toggle-active');
                }
                postHttpRequest("setFreeplayEnabled", {isFreeplayEnabled});
                return
            } else if (keyCode == 27 && actionType == 'keydown' && $('#controls-fullscr-btn').hasClass('fullscr-btn-active')){
                toggleFullScreen();
            }
        }
        postHttpRequest(actionType, {keyCode: logicalKeyCode, hasShift, hasCtrl, hasAlt});
    }
}

// create and place
let initControlButtons = function(){
    let controlButtons = [
        ['W', 247, 25],  // forward
        ['S', 247, 93],  // back
        ['A', 193, 59],  // left
        ['D', 301, 59],  // right
        ['Q', 16, 59],   // head up
        ['E', 70, 59],   // head down
        ['R', 424, 59],  // arm up
        ['F', 478, 59]  // arm down
    ];

    let controlStates = [
        ['SHIFT', 131, 137],
        ['ALT', 337, 137]
    ];

    let toggleButtons = [
        ['I', 567, 37],  // IR light toggle
        ['P', 567, 120]  // Free Play toggle
    ];

    for (let i = 0; i < controlButtons.length; i++){
        let logicalKey = controlButtons[i][0];
        let bID = 'ctrl_btn_' + logicalKey;
        $('#controls-content').append('<div id="'+ bID + '" class="control-button">' + getLayoutLabel(logicalKey) + '</div>');
        let btn = $('#' + bID);
        btn.css({
            left: controlButtons[i][1],
            top: controlButtons[i][2]
        });
        btn.mousedown(function(){
            mouseKeyCode = $(this).attr('id').charCodeAt(9);
            $(this).addClass('control-button-active');
/*
            mousedownInterval = setInterval(function(){
                console.log(mouseKeyCode);
                postHttpRequest('keydown', {keyCode: mouseKeyCode, hasShift:0, hasCtrl:0, hasAlt:0})
            }, 100);
*/
        });
        btn.mouseup(function(){
            clearInterval(mousedownInterval);
            $(this).removeClass('control-button-active');
        });
        btn.mouseleave(function () {
            clearInterval(mousedownInterval);
            $(this).removeClass('control-button-active');
        });
    }
    for (let j=0; j < controlStates.length; j++){
        let bID = 'ctrl_state_' + controlStates[j][0];
        $('#controls-content').append('<div id="'+ bID + '" class="control-state">' + controlStates[j][0] + '</div>');
        let state = $('#' + bID);
        state.css({
            left: controlStates[j][1],
            top: controlStates[j][2]
        });
    }
    for (let k=0; k < toggleButtons.length; k++){
        let bID = 'ctrl_toggle_' + toggleButtons[k][0];
        $('#controls-content').append('<div id="'+ bID + '" class="control-toggle">' + toggleButtons[k][0] + '</div>');
        let btn = $('#' + bID);
        btn.css({
           left: toggleButtons[k][1],
           top: toggleButtons[k][2]
        });
        btn.mousedown(function(){
            mouseKeyCode = $(this).attr('id').charCodeAt(12);
            console.log(mouseKeyCode);
            if(mouseKeyCode == 73){
                // toggle IR headlight
                isHeadlightEnabled = !isHeadlightEnabled;
                postHttpRequest("setHeadlightEnabled", {isHeadlightEnabled});
            }
            if(mouseKeyCode == 80){
                // toggle free play mode
                isFreeplayEnabled = !isFreeplayEnabled;
                postHttpRequest("setFreeplayEnabled", {isFreeplayEnabled});
            }
            if ($(this).hasClass('control-toggle-active')){
                $(this).removeClass('control-toggle-active');
            } else {
                $(this).addClass('control-toggle-active');
            }
/*
            postHttpRequest('keydown', mouseKeyCode);
*/
        });
    }
    updateControlButtonLabels();
};

// creating animation list with or without group buttons
let initAnimationList = function(fragment, listType){
    fragment.load('/static/includes/animate.html', function(){

        for(let i = 0; i < listArray.length; i++){
            if(listArray[i].name == listType){
                createList(listArray[i]);
                if(listType == 'animations'){
                    createGroupButtons();
                    $('#group-btns').show();
                } else $('#group-btns').hide();
                initSearch();
                let str = listArray[i].str;
                $('.search').val(str);
                matchCharacters(str);
            }
        }

        $('#group-header').click(function () {
            if ($('#group-content').hasClass('hidden')) {
                $('#group-content').removeClass('hidden');
                $('#group-header i').switchClass('fa-caret-square-o-up', 'fa-caret-square-o-down');
            } else {
                $('#group-content').addClass('hidden');
                $('#group-header i').switchClass('fa-caret-square-o-down', 'fa-caret-square-o-up');
            }
        });

        $('#search-field').focus(function (){
           isFocusOnInput = true;
        });
        $('#search-field').blur(function (){
           isFocusOnInput = false;
        });

    });
};

let toggleFullScreen = function(){
    if($('#controls-fullscr-btn').hasClass('fullscr-btn-active')){
        $('#controls').append($('#controls-fullscr-btn'));
        $('#controls-fullscr-btn').removeClass('fullscr-btn-active');
        $('#content').show();
        $('#header').show();
        $('#viewer-content').prepend($('#cozmoImageId'));
        $('#viewer-content').prepend($('#viewer-bg'));
        $('#cover-all').remove();
    } else {
        $('#content').hide();
        $('#header').hide();
        $('body').append('<div id="cover-all"></div>');
        $('#cover-all').append($('#cozmoImageId'));
        $('#cover-all').append($('#controls-fullscr-btn'));
        $('#controls-fullscr-btn').addClass('fullscr-btn-active');
    }
};

let toggleViewerVisible = function(){
    if ($('#viewer').hasClass('hidden')) {
        $('#viewer').removeClass('hidden');
        $('#event-header b i').switchClass('fa-caret-square-o-down', 'fa-caret-square-o-up');
        imageInterval = setInterval(updateImage, 90);
    } else {
        $('#viewer').addClass('hidden');
        $('#event-header b i').switchClass('fa-caret-square-o-up', 'fa-caret-square-o-down');
        clearInterval(imageInterval);
    }
};

/*** INITIALIZATION ***/
function initializeCozmoExplorer() {
    applyDemoListsIfNeeded();
    refreshListArrays();

    // creating list of cozmo animations (active tab)
    animateHTML = document.querySelector('link[rel="import"]');
    initAnimationList($('#fragment-0'), 'animations');

    // enable clipboard copy button
    $('#btn-copy').click(function(){
        copyTextToClipboard($('#mono').text());
        $('#status').text('copied to clipboard');
        $('#mono').effect( 'transfer', {to: '#btn-copy', className: 'ui-effects-transfer'}, 300);
        $(this).css({'background-color': '#05BE00', 'color': '#ffffff'});
    });

    // jquery ui tabs behaviour definition
    $( "#tabs" ).tabs({
        heightStyle: 'content',
        beforeActivate: function(event, ui){
            if(isRunning){
                getHttpRequest('stop', ''); // abort any running action before switching tabs
                checkRunning(false);
            }
            for (let i = 0; i < listArray.length; i++){
                if (listArray[i].name == currentTab){
                    listArray[i].str = $('.search').val();
                }
            }
            let idStr = ui.newTab.attr('aria-controls');
            let oldStr = ui.oldTab.attr('aria-controls');
            let id = Number(idStr.substr(9));
            let name = listArray[id].name;
            currentTab = name;
            $('#' + oldStr).html('');
            initAnimationList($('#' + idStr), currentTab);
        },
        classes: {
            'ui-tabs-nav': 'tabs-nav',
            'ui-tabs': 'tabs'
        }
    });

    // jquery ui tabs css tweaking
    $('#tablist').removeClass('ui-corner-all');

    // global mousedown detection: to prevent animation list-buttons
    // from being created while mouse is pressed
    $('body').mousedown(function () {
        isMouseDown = true;
    });
    $('body').mouseup(function () {
        isMouseDown = false;
    });

    // return to pose after animation button and tooltip
    $('#pose-btn').click(function(){
        if($('#pose-btn').hasClass('pose-btn-active')){
            $('#pose-btn').removeClass('pose-btn-active');
        } else {
            $('#pose-btn').addClass('pose-btn-active');
        }
        getHttpRequest('toggle_pose', '');
    });
    $('#pose-btn').mouseenter(function(){
       $('#pose-tt').fadeTo(500, 1);
    });
    $('#pose-btn').mouseleave(function(){
       $('#pose-tt').fadeTo(250, 0);
    });


    // event monitor enlarger button, hides camera viewer
    $('#event-header b i').click(function () {
        toggleViewerVisible();
    });

    // create and place buttons for cozmo control
    initKeyboardLayoutToggle();
    initControlButtons();

    // start camera image stream
    imageInterval = setInterval(updateImage, 90);

    // clicking on camera image pauses stream
/*    $('#cozmoImageId').click(function () {
        if($('#cozmoImageId').hasClass('stopped')){
            $('#cozmoImageId').removeClass('stopped');
            imageInterval = setInterval(updateImage, 90);
        } else {
            $('#cozmoImageId').addClass('stopped');
            clearInterval(imageInterval);
        }
    });*/

    // when the app starts and the mouse is not over the camera viewer area
    // after 2 seconds, do a fade of the controls.
    setTimeout(function () {
        if($('#viewer:hover').length == 0){
            $('#controls').fadeTo(500 , 0);
        }
    }, 2000);

    // hovering over camera viewer causes control buttons to appear
    $('#viewer').mouseenter(function () {
        $('#controls').fadeTo(500 , 1);
        // $('#controls').show();
    });
    $('#viewer').mouseleave(function () {
        $('#controls').fadeTo(500 , 0);
        // $('#controls').hide();
    });

    // button with left aligned lines toggles pose and accellerometer info.
    // By default turned on.
    $('#controls-info-btn').click(function () {
        let debug_annotation_state;
        if($('#controls-info-btn').hasClass('info-btn-active')){
            $('#controls-info-btn').removeClass('info-btn-active');
            debug_annotation_state = 2;
        } else {
            $('#controls-info-btn').addClass('info-btn-active');
            debug_annotation_state = 1;
        }
        postHttpRequest("setAreDebugAnnotationsEnabled", {areDebugAnnotationsEnabled: debug_annotation_state})
    });

    // button with expand arrows toggles full screen camera mode.
    // By default turned off.
    $('#controls-fullscr-btn').click(function () {
        toggleFullScreen();
    });

    // checks if the python module flasksocket-io is installed.
    // If not, event monitoring will not work and an message appears in the event monitor section.
    if (window.COZMO_APP.hasSocketIO) {
        init_websocket();
    } else {
        $('#event-content').append('<li style="background-color: lightcoral">flask-socketio not installed, event monitoring only visible on python console or terminal window</li>');
    }

    if (!window.COZMO_APP.hasPillow) {
        $('#event-content').append('<li style="background-color: lightcoral">Pillow not installed. Run: pip install Pillow</li>');
    } else if (!window.COZMO_APP.hasCamera || !window.COZMO_APP.robotConnected) {
        $('#event-content').append('<li class="demo-reconnect-msg" style="background-color: lightcoral">Demo mode: Cozmo not connected. Connect PC to Cozmo-XXXX Wi-Fi; the app will connect automatically.</li>');
        startRobotReconnectPoll();
    }

    if (window.COZMO_APP.robotConnected) {
        startCozmoUpdateLoop();
    }

    document.addEventListener("keydown", function(e) { handleKeyActivity(e, "keydown") } );
    document.addEventListener("keyup",   function(e) { handleKeyActivity(e, "keyup") } );
}

$( function () {
    loadCozmoBootstrap(function (bootstrapOk) {
        if (!bootstrapOk && window.COZMO_APP.robotConnected) {
            $('#event-content').append('<li style="background-color: lightcoral">Error: could not load /ui-bootstrap. Stop all Python servers, restart explorer_tool.py, then press Ctrl+F5.</li>');
        }
        initializeCozmoExplorer();
    });
});
